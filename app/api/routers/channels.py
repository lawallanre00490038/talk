# app/api/routers/channels.py
from fastapi import APIRouter, Depends, HTTPException, status
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.db.models import  Channel, Post, UserChannelLink
from app.core.config import settings
from app.schemas.channel import ChannelCreate, ChannelPublic
from app.schemas.auth import TokenUser
from app.schemas.post import PostPublic
from app.db.repositories.base import BaseRepository
from app.api.deps import pagination_params

router = APIRouter()
channel_repo = BaseRepository(Channel)
post_repo = BaseRepository(Post)

@router.post("/", response_model=ChannelPublic, status_code=status.HTTP_201_CREATED)
async def create_channel(
    *,
    session: AsyncSession = Depends(get_session),
    channel_in: ChannelCreate,
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """
    Create a new channel. The creator automatically becomes an admin member.
    """
    channel = Channel.from_orm(channel_in, update={"created_by": current_user.id})
    
    # Add creator as the first member and admin
    link = UserChannelLink(user_id=current_user.id, channel_id=channel.id, is_admin=True)
    channel.members.append(current_user) # This relationship is managed via the link model
    
    session.add(channel)
    session.add(link)
    await session.commit()
    await session.refresh(channel)
    
    return channel

@router.post("/{channel_id}/join", status_code=status.HTTP_204_NO_CONTENT)
async def join_channel(
    channel_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """
    Join a public channel.
    """
    channel = await channel_repo.get(session, id=channel_id)
    if not channel or channel.is_private:
        raise HTTPException(status_code=404, detail="Channel not found or is private")

    # Check if user is already a member
    statement = select(UserChannelLink).where(UserChannelLink.user_id == current_user.id, UserChannelLink.channel_id == channel_id)
    result = await session.execute(statement)
    if result.scalars().first():
        return # Already a member, do nothing

    link = UserChannelLink(user_id=current_user.id, channel_id=channel_id)
    session.add(link)
    await session.commit()
    return



@router.get("/{channel_id}/posts", response_model=List[PostPublic])
async def get_posts_in_channel(
    channel_id: str,
    session: AsyncSession = Depends(get_session),
    pagination: pagination_params = Depends(),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)), # Ensures user is logged in
):
    """
    Get the feed for a specific channel.
    """
    # In a real app, you'd also check if the user is a member of a private channel
    statement = (
        select(Post)
        .where(Post.channel_id == channel_id)
        .options(selectinload(Post.author))
        .order_by(Post.created_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    result = await session.execute(statement)
    posts = result.scalars().all()
    return posts