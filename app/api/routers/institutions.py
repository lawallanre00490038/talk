from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from typing import List

from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.core.config import settings
from app.db.models import Institution, Post, UploadedDocument, UserRole, PostPrivacy, StudentProfile
from app.schemas.institution import InstitutionPublic, UploadedDocumentCreate, UploadedDocumentPublic, InstitutionTimelineResponse, PostPublic
from app.schemas.auth import TokenUser
from app.db.repositories.institution_repo import institution_repo
from app.services.rag_service import ingest_document_background

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


@router.get("/{institution_id}/posts", response_model=List)
async def list_institution_posts(
    institution_id: str,
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 50,
):
    # Return posts whose school_scope matches institution name
    inst = await institution_repo.get(session, id=institution_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    statement = (
        select(Post)
        .where(Post.school_scope == inst.institution_name)
        .options(selectinload(Post.author), selectinload(Post.media), selectinload(Post.comments))
        .order_by(Post.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(statement)
    posts = result.scalars().all()
    return posts


@router.post("/{institution_id}/posts", status_code=status.HTTP_201_CREATED)
async def create_institution_post(
    institution_id: str,
    content: str,
    post_type: str = "post",
    mirror_to_general: bool = False,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    # Only institution users that own this institution can post here
    if current_user.role != UserRole.INSTITUTION:
        raise HTTPException(status_code=403, detail="Only institution accounts can create institution posts")

    inst = await institution_repo.get(session, id=institution_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Ensure current_user has an institution_profile that matches this institution
    # (InstitutionProfile is stored in db.models and created earlier by /profile/institution)
    # Verify user is an admin/owner for this institution
    is_admin = await institution_repo.is_user_institution_admin(session, current_user.id, institution_id)
    if not is_admin and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You are not an admin for this institution")

    # If mirror_to_general is True, the post should appear on the general feed as well
    if mirror_to_general:
        post = Post(
            author_id=current_user.id,
            content=content,
            post_type=post_type,
            privacy=PostPrivacy.PUBLIC,
            school_scope=None,
        )
    else:
        post = Post(
            author_id=current_user.id,
            content=content,
            post_type=post_type,
            privacy=PostPrivacy.SCHOOL_ONLY,
            school_scope=inst.institution_name,
        )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post


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
    background_tasks.add_task(ingest_document_background, created.id, created.file_url, institution_id)

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
    from app.services.rag_service import rag_service

    inst = await institution_repo.get(session, id=institution_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    result = await rag_service.query(institution_id, query, top_k=3)
    return {
        "success": result["success"],
        "answer": result["answer"],
        "sources": result["sources"],
        "institution_id": institution_id,
    }
