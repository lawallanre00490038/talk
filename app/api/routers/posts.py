# app/api/routers/posts.py
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from typing import List, Optional
import cloudinary
import cloudinary.uploader

from app.core.config import settings
from app.core.auth import get_current_user_dependency
from app.db.session import get_session
from app.db.models import Media, MediaType, PostPrivacy, User, Post, UserRole, PostType
from app.schemas.auth import TokenUser
from app.schemas.post import PostCreate, PostPublic, PresignedUrlResponse
from app.db.repositories.post_repo import post_repo
from app.services.media_service import media_service
from app.api.deps import pagination_params
from app.tasks.media_tasks import process_video_thumbnail

router = APIRouter()


@router.post("/", response_model=PostPublic, status_code=status.HTTP_201_CREATED)
async def create_post(
    *,
    session: AsyncSession = Depends(get_session),
    background_tasks: BackgroundTasks,
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),

    # form fields
    content: str = Form(...),
    privacy: PostPrivacy = Form(PostPrivacy.PUBLIC),
    post_type: PostType = Form(PostType.POST),
    is_school_scope: bool = Form(False),

    # media
    images: Optional[list[UploadFile]] = File(None),
    video: Optional[UploadFile] = File(None),
):
    """
    Create a new post (regular or reel).

    For posts with media:
    - Get a presigned URL from `/media/presigned-url`.
    - Upload the file to S3.
    - Include the media URL in the `content` or media list.
    """

    # -----------------------------
    # VALIDATION
    # -----------------------------
    if images and video:
        raise HTTPException(400, "Cannot upload images and video together")

    if post_type == PostType.REEL and not video:
        raise HTTPException(400, "Reel post requires a video")

    if post_type == PostType.POST and not (content or images):
        raise HTTPException(400, "Post must have text or image")

    # -----------------------------
    # SCHOOL SCOPE AUTO-SET
    # -----------------------------
    # -----------------------------
    # GET INSTITUTION ID
    # -----------------------------
    final_institution_id = None
    if is_school_scope:
        user = await session.get(
            User,
            current_user.id,
            options=[
                selectinload(User.student_profile),
                selectinload(User.institution_profile),
            ],
        )
        
        # Check profiles for the ID
        if user.institution_profile:
            final_institution_id = user.institution_profile.institution_id
        elif user.student_profile:
            final_institution_id = user.student_profile.institution_id
            
        if not final_institution_id:
             raise HTTPException(400, "User is not linked to a valid institution")

    post = Post(
        author_id=current_user.id,
        content=content,
        post_type=post_type,
        privacy=privacy,
        school_scope=final_institution_id,
    )

    session.add(post)
    await session.flush()

    # -----------------------------
    # HANDLE MEDIA UPLOADS
    # -----------------------------
    media_objects: list[Media] = []

    if images:
        for img in images:
            if img.content_type not in ["image/jpeg", "image/png"]:
                raise HTTPException(400, "Only JPG and PNG images allowed")

            upload = cloudinary.uploader.upload(
                img.file,
                folder="posts/images",
                resource_type="image",
            )

            media_objects.append(
                Media(
                    post_id=post.id,
                    media_type=MediaType.IMAGE,
                    url=upload["secure_url"],
                    file_metadata={
                        "width": upload.get("width"),
                        "height": upload.get("height"),
                        "format": upload.get("format"),
                        "bytes": upload.get("bytes"),
                    },
                )
            )

    if video:
        if video.content_type not in ["video/mp4", "video/quicktime"]:
            raise HTTPException(400, "Only MP4 or MOV videos allowed")

        upload = cloudinary.uploader.upload(
            video.file,
            folder="posts/videos",
            resource_type="video",
        )

        media_objects.append(
            Media(
                post_id=post.id,
                media_type=MediaType.VIDEO,
                url=upload["secure_url"],
                file_metadata={
                    "duration": upload.get("duration"),
                    "format": upload.get("format"),
                    "bytes": upload.get("bytes"),
                },
            )
        )

    session.add_all(media_objects)

    # -----------------------------
    # COMMIT ONCE (ATOMIC)
    # -----------------------------
    await session.commit()
    await session.refresh(post)

    # -----------------------------
    # BACKGROUND VIDEO PROCESSING
    # -----------------------------
    if post_type == PostType.REEL and media_objects:
        background_tasks.add_task(
            process_video_thumbnail,
            post_id=post.id,
            video_url=media_objects[0].url,
        )

    # -----------------------------
    # RESPONSE
    # -----------------------------
    result = await session.execute(
        select(Post)
        .options(
            selectinload(Post.author),
            selectinload(Post.media),
        )
        .where(Post.id == post.id)
    )

    return result.scalar_one()






@router.get("/media/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_upload_url(
    *,
    file_name: str,
    file_type: str,  # e.g., "image/jpeg", "video/mp4"
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """
    Get a pre-signed S3 upload URL to directly upload media from the client.
    """
    url_data = media_service.generate_presigned_upload_url(file_name, file_type)
    if not url_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL. Please try again later.",
        )
    return {"upload_url": url_data["upload_url"], "file_key": url_data["file_key"]}


@router.get("/", response_model=List[PostPublic])
async def read_posts(
    *,
    session: AsyncSession = Depends(get_session),
    pagination: pagination_params = Depends(),
    school_scope: Optional[str] = None,
):
    """
    Retrieve posts for the main feed (type = POST).
    Can filter by school scope.
    """
    stmt = (
        select(Post)
        .where(Post.post_type == PostType.POST)
        .options(selectinload(Post.author))
        .order_by(Post.created_at.desc())
    )
    if school_scope:
        stmt = stmt.where(Post.school_scope == school_scope)

    stmt = stmt.offset(pagination.skip).limit(pagination.limit)
    posts = (await session.execute(stmt)).scalars().all()
    return posts


@router.get("/reels", response_model=List[PostPublic])
async def read_reels(
    *,
    session: AsyncSession = Depends(get_session),
    pagination: pagination_params = Depends(),
):
    """
    Retrieve all posts of type 'reel'.
    """
    return await post_repo.get_reels(session, skip=pagination.skip, limit=pagination.limit)


@router.get("/{post_id}", response_model=PostPublic)
async def read_post(
    *,
    post_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get a single post by its ID, including author info.
    """
    post = await post_repo.get_by_id_with_author(session, id=post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post





@router.get("/institution/{institution_id}", response_model=List[PostPublic])
async def get_posts_by_institution(
    *,
    institution_id: str,
    session: AsyncSession = Depends(get_session),
    pagination: pagination_params = Depends(),
    post_type: Optional[PostType] = None
):
    """
    Fetch all posts belonging to a specific institution by ID.
    """
    stmt = (
        select(Post)
        .where(Post.school_scope == institution_id)
        .options(
            selectinload(Post.author),
            selectinload(Post.media)
        )
        .order_by(Post.created_at.desc())
    )
    
    if post_type:
        stmt = stmt.where(Post.post_type == post_type)

    stmt = stmt.offset(pagination.skip).limit(pagination.limit)
    
    result = await session.execute(stmt)
    return result.scalars().all()




@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    *,
    session: AsyncSession = Depends(get_session),
    post_id: str,
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """
    Delete a post. Only the post author or an admin can delete.
    """
    post = await post_repo.get(session, id=post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this post.",
        )

    await session.delete(post)
    await session.commit()
