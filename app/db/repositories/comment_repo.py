# app/db/repositories/comment_repo.py
from typing import List
import uuid
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Comment
from app.db.repositories.base import BaseRepository

class CommentRepository(BaseRepository[Comment]):
    async def get_comments_for_post(
        self, session: AsyncSession, *, post_id: str, skip: int = 0, limit: int = 25
    ) -> List[Comment]:
        statement = (
            select(Comment)
            .where(Comment.post_id == post_id)
            .options(selectinload(Comment.author))
            .order_by(Comment.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(statement)
        return result.scalars().all()

comment_repo = CommentRepository(Comment)