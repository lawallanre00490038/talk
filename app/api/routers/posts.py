# app/api/routers/posts.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from typing import List, Optional

from app.core.config import settings
from app.core.auth import get_current_user_dependency
from app.db.session import get_session
from app.db.models import User, Post, UserRole, PostType
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
    post_in: PostCreate,
    background_tasks: BackgroundTasks,
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """
    Create a new post (regular or reel).

    For posts with media:
    - Get a presigned URL from `/media/presigned-url`.
    - Upload the file to S3.
    - Include the media URL in the `content` or media list.
    """
    post_data = post_in.model_dump()
    post_data["author_id"] = current_user.id

    # Automatically set school_scope for student posts if applicable
    if post_in.school_scope and current_user.role == UserRole.STUDENT:
        user = await session.get(User, current_user.id, options=[selectinload(User.student_profile)])
        post_data["school_scope"] = (
            user.student_profile.institution_name if user and user.student_profile else None
        )

    post = Post(**post_data)
    new_post = await post_repo.create(session, obj_in=post)



    # If it's a video (reel), trigger background thumbnail generation
    if new_post.post_type == PostType.REEL:
        background_tasks.add_task(process_video_thumbnail, post_id=new_post.id)

    # Reload post with author for full response
    result = await session.execute(
        select(Post)
        .options(selectinload(Post.author))
        .where(Post.id == new_post.id)
    )

    post_to_send =  result.scalar_one()

    return post_to_send

    


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
