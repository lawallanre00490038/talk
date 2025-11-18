# app/api/routers/likes.py
from fastapi import APIRouter, Depends, status, HTTPException
import uuid
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.db.models import User, Like, Post
from app.core.config import settings
from app.db.repositories.base import BaseRepository
from app.schemas.auth import TokenUser

router = APIRouter()
like_repo = BaseRepository(Like)
post_repo = BaseRepository(Post)

@router.post("/post/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def toggle_like_post(
    post_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings))
):
    post = await post_repo.get(session, id=post_id, options=[selectinload(Post.author)])
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    # Check if a like already exists
    statement = select(Like).where(Like.user_id == current_user.id, Like.post_id == post_id)
    result = await session.execute(statement)
    existing_like = result.scalars().first()
    
    if existing_like:
        # Unlike
        await session.delete(existing_like)
        await session.commit()
    else:
        # Like
        like = Like(user_id=current_user.id, post_id=post_id)
        await like_repo.create(session, obj_in=like)
    
    return
