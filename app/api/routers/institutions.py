import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.api.deps import pagination_params
from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.core.config import settings
from app.db.models import Institution, Media, MediaType, Post, PostType, UploadedDocument, UserRole, PostPrivacy, StudentProfile
from app.schemas.institution import InstitutionPublic, UploadedDocumentCreate, UploadedDocumentPublic, InstitutionTimelineResponse, PostPublic
from app.schemas.auth import TokenUser
from app.db.repositories.institution_repo import institution_repo
from app.tasks.media_tasks import process_video_thumbnail
# from app.services.rag_service import ingest_document_background

router = APIRouter()


@router.get("/{institution_id}", response_model=InstitutionPublic)
async def get_institution(
    institution_id: str,
    session: AsyncSession = Depends(get_session),
):
    inst = await institution_repo.get(session, id=institution_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    posts_count = await institution_repo.get_posts_count(session, inst)
    students_count = len(inst.students) if hasattr(inst, "students") else 0

    return InstitutionPublic.model_validate({
        **inst.model_dump(),
        "students_count": students_count,
        "posts_count": posts_count,
    })




@router.get("/{institution_id}/posts", response_model=List[PostPublic])
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





@router.post("/{institution_id}/posts", response_model=PostPublic, status_code=status.HTTP_201_CREATED)
async def create_institution_post(
    institution_id: str,
    content: str = Form(...),
    post_type: PostType = Form(PostType.POST),
    mirror_to_general: bool = Form(False),
    images: Optional[list[UploadFile]] = File(None),
    video: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    # 1. PERMISSION CHECK
    if current_user.role not in [UserRole.INSTITUTION, UserRole.ADMIN]:
        raise HTTPException(403, "Only institution accounts can create official posts")

    is_admin = await institution_repo.is_user_institution_admin(session, current_user.id, institution_id)
    if not is_admin and current_user.role != UserRole.ADMIN:
        raise HTTPException(403, "You are not an admin for this institution")

    # 2. VALIDATE MEDIA (Same as general post)
    if images and video:
        raise HTTPException(400, "Cannot upload images and video together")
    if post_type == PostType.REEL and not video:
        raise HTTPException(400, "Reel post requires a video")

    # 3. INITIALIZE POST
    privacy = PostPrivacy.PUBLIC if mirror_to_general else PostPrivacy.SCHOOL_ONLY
    post = Post(
        author_id=current_user.id,
        content=content,
        post_type=post_type,
        privacy=privacy,
        school_scope=institution_id, 
    )
    session.add(post)
    await session.flush() # Get post.id for media links

    # 4. HANDLE IMAGE UPLOADS
    media_objects: list[Media] = []
    if images:
        for img in images:
            # You can extract this to a service.upload_media function
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
                    file_metadata={"format": upload.get("format"), "bytes": upload.get("bytes")}
                )
            )

    # 5. HANDLE VIDEO UPLOADS
    if video:
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
                file_metadata={"duration": upload.get("duration"), "bytes": upload.get("bytes")}
            )
        )

    if media_objects:
        session.add_all(media_objects)

    # 6. ATOMIC COMMIT
    await session.commit()
    await session.refresh(post)

    # 7. TRIGGER BACKGROUND TASKS (Reels)
    if post_type == PostType.REEL and media_objects:
        background_tasks.add_task(
            process_video_thumbnail, # Assuming this is imported
            post_id=post.id,
            video_url=media_objects[0].url,
        )

    # 8. FETCH FULL OBJECT FOR RESPONSE
    result = await session.execute(
        select(Post).options(selectinload(Post.author), selectinload(Post.media)).where(Post.id == post.id)
    )
    return result.scalar_one()




@router.post("/{institution_id}/documents", response_model=UploadedDocumentPublic, status_code=status.HTTP_201_CREATED)
async def upload_document_for_rag(
    institution_id: str,
    doc_in: UploadedDocumentCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    inst = await institution_repo.get(session, id=institution_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Only institution users or admins can upload
    if current_user.role not in (UserRole.INSTITUTION, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not allowed to upload documents")

    # Verify user is an admin/owner for this institution
    is_admin = await institution_repo.is_user_institution_admin(session, current_user.id, institution_id)
    if not is_admin and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You are not an admin for this institution")

    # Persist document record
    doc = UploadedDocument(
        institution_id=institution_id,
        title=doc_in.title,
        description=doc_in.description,
        file_url=doc_in.file_url,
        uploaded_by=current_user.id,
    )
    created = await institution_repo.create_document(session, obj_in=doc)

    # Enqueue RAG ingestion in background
    # background_tasks.add_task(ingest_document_background, created.id, created.file_url, institution_id)

    return created


@router.get("/{institution_id}/documents", response_model=List[UploadedDocumentPublic])
async def list_documents(
    institution_id: str,
    session: AsyncSession = Depends(get_session),
):
    inst = await institution_repo.get(session, id=institution_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    docs = await institution_repo.get_documents_for_institution(session, institution_id)
    return docs


@router.get("/documents/{document_id}", response_model=UploadedDocumentPublic)
async def get_document(document_id: str, session: AsyncSession = Depends(get_session)):
    doc = await institution_repo.get_document(session, id=document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, session: AsyncSession = Depends(get_session), current_user: TokenUser = Depends(get_current_user_dependency(settings=settings))):
    doc = await institution_repo.get_document(session, id=document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.uploaded_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not allowed to delete this document")

    await session.delete(doc)
    await session.commit()
    return


@router.get("/timeline/my-institution", response_model=InstitutionTimelineResponse)
async def get_my_institution_timeline(
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """
    Get the logged-in student's institution timeline.
    Returns the institution details + all school-scoped posts for that institution.
    """
    # Only students can access this
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can view institution timelines")

    # Fetch student profile to get institution_id
    statement = select(StudentProfile).where(StudentProfile.user_id == current_user.id).options(selectinload(StudentProfile.institution))
    result = await session.execute(statement)
    student_profile = result.scalars().first()

    if not student_profile or not student_profile.institution_id:
        raise HTTPException(status_code=404, detail="Student profile or institution not found")

    # Get institution
    institution = await institution_repo.get(session, id=student_profile.institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Get posts for this institution (school-scoped posts only)
    posts_statement = (
        select(Post)
        .where(Post.school_scope == institution.institution_name)
        .options(selectinload(Post.author), selectinload(Post.media), selectinload(Post.comments))
        .order_by(Post.created_at.desc())
    )
    posts_result = await session.execute(posts_statement)
    posts = posts_result.scalars().all()

    # Compute stats
    posts_count = len(posts)
    students_count = len(institution.students) if hasattr(institution, "students") else 0

    # Build response
    institution_data = InstitutionPublic.model_validate({
        **institution.model_dump(),
        "students_count": students_count,
        "posts_count": posts_count,
    })

    posts_data = [PostPublic.model_validate(post) for post in posts]

    return InstitutionTimelineResponse(institution=institution_data, posts=posts_data)


@router.post("/{institution_id}/chatbot")
async def chatbot_query(
    institution_id: str,
    query: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """Query the RAG chatbot for an institution."""
    # from app.services.rag_service import rag_service

    inst = await institution_repo.get(session, id=institution_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    # result = await rag_service.query(institution_id, query, top_k=3)
    return {
        # "success": result["success"],
        # "answer": result["answer"],
        # "sources": result["sources"],
        "institution_id": institution_id,
    }
