# app/api/routers/complaints.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.db.models import User, Complaint
from app.schemas.auth import TokenUser
from app.schemas.complaints import ComplaintCreate, ComplaintPublic
from app.db.repositories.base import BaseRepository
from app.core.config import settings

router = APIRouter()
complaint_repo = BaseRepository(Complaint)

@router.post("/", response_model=ComplaintPublic, status_code=status.HTTP_201_CREATED)
async def file_complaint(
    *,
    session: AsyncSession = Depends(get_session),
    complaint_in: ComplaintCreate,
    current_user: TokenUser = Depends(get_current_user_dependency(settings)),
):
    """
    File a complaint against a post, comment, or user.
    """
    num_targets = sum(
        1 for item in 
        [complaint_in.reported_post_id, complaint_in.reported_comment_id, complaint_in.reported_user_id] 
        if item is not None
    )
    if num_targets != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly one of reported_post_id, reported_comment_id, or reported_user_id must be provided."
        )

    complaint = Complaint.from_orm(complaint_in, update={"reporter_id": current_user.id})
    new_complaint = await complaint_repo.create(session, obj_in=complaint)
    return new_complaint