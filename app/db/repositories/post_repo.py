# app/db/repositories/post_repo.py
from typing import List, Optional
import uuid
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Post, PostType
from app.db.repositories.base import BaseRepository

class PostRepository(BaseRepository[Post]):
    async def get_all_with_author(
        self, session: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Post]:
        statement = (
            select(Post)
            .options(selectinload(Post.author))
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(statement)
        return result.scalars().all()

    async def get_by_id_with_author(self, session: AsyncSession, *, id: str) -> Optional[Post]:
        statement = select(Post).where(Post.id == id).options(selectinload(Post.author))
        result = await session.execute(statement)
        return result.scalars().first()

    async def get_reels(
        self, session: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Post]:
        statement = (
            select(Post)
            .where(Post.post_type == PostType.REEL)
            .options(selectinload(Post.author))
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(statement)
        return result.scalars().all()

post_repo = PostRepository(Post)