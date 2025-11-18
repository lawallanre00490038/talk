# app/api/routers/notifications.py
from fastapi import APIRouter, Depends, status
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.db.models import  Notification
from app.schemas.auth import TokenUser
from app.schemas.notifications import NotificationPublic
from app.api.deps import pagination_params
from app.core.config import settings

router = APIRouter()

@router.get("/me", response_model=List[NotificationPublic])
async def get_my_notifications(
    session: AsyncSession = Depends(get_session),
    pagination: pagination_params = Depends(),
    current_user: TokenUser = Depends(get_current_user_dependency(settings)),
):
    """
    Get the current user's notifications, most recent first.
    """
    statement = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .options(selectinload(Notification.user))
        .order_by(Notification.created_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    result = await session.execute(statement)
    notifications = result.scalars().all()
    return notifications

@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_as_read(
    notification_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings)),
):
    """
    Mark a single notification as read.
    """
    statement = (
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == current_user.id)
        .values(is_read=True)
    )
    await session.execute(statement)
    await session.commit()
    return
