# app/api/routers/admin.py
from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.auth import require_admin
from app.db.models import User, Complaint
from app.schemas.auth import UserPublic
from app.api.deps import pagination_params
from app.db.repositories.base import BaseRepository

router = APIRouter()
complaint_repo = BaseRepository(Complaint)
user_repo = BaseRepository(User)

@router.get("/users", response_model=List[UserPublic])
async def get_all_users(
    session: AsyncSession = Depends(get_session),
    pagination: pagination_params = Depends(),
    current_admin: User = Depends(require_admin)
):
    """
    (Admin) Get a list of all users.
    """
    users = await user_repo.get_all(session, skip=pagination.skip, limit=pagination.limit)
    return users


@router.get("/complaints", response_model=List[Complaint])
async def get_all_complaints(
    session: AsyncSession = Depends(get_session),
    pagination: pagination_params = Depends(),
    current_admin: User = Depends(require_admin)
):
    """
    (Admin) Get all filed complaints.
    """
    complaints = await complaint_repo.get_all(session, skip=pagination.skip, limit=pagination.limit)
    return complaints