# app/api/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.db.models import User
from app.schemas.auth import TokenUser, UserPublic
from app.db.repositories.user_repo import user_repo

router = APIRouter()

@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: TokenUser = Depends(get_current_user_dependency(settings=settings))):
    """
    Get current user's profile.
    """
    return current_user

@router.get("/{user_id}", response_model=UserPublic)
async def read_user_by_id(
    user_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Get a specific user's public profile by ID.
    """
    user = await user_repo.get(session, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user