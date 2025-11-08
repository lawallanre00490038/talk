# app/services/notification_service.py
import logging
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.manager import manager
from app.db.models import Notification, NotificationType
from app.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, repository: BaseRepository[Notification]):
        self.repository = repository

    async def create_notification(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        notification_type: NotificationType,
        content: dict
    ):
        """
        Creates a notification in the DB and attempts to send it via WebSocket.
        """
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            content=content
        )
        await self.repository.create(session, obj_in=notification)
        logger.info(f"Notification created for user {user_id}")

        # Send real-time notification via WebSocket
        try:
            message = f"notification:{notification_type.value}:{content.get('message', '')}"
            await manager.send_personal_message(message, str(user_id))
            logger.info(f"WebSocket notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification to user {user_id}: {e}")

notification_service = NotificationService(BaseRepository(Notification))