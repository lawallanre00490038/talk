# app/api/routers/communities.py
from tokenize import Token
from fastapi import APIRouter, Depends, HTTPException, status
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.db.models import User, Community, Post
from app.schemas.post import PostPublic
from app.schemas.auth import TokenUser
from app.schemas.channel import CommunityCreate, CommunityPublic
from app.db.repositories.base import BaseRepository
from app.api.deps import pagination_params
from app.core.config import settings

router = APIRouter()
community_repo = BaseRepository(Community)

@router.post("/", response_model=CommunityPublic, status_code=status.HTTP_201_CREATED)
async def create_community(
    *,
    session: AsyncSession = Depends(get_session),
    community_in: CommunityCreate,
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """
    Create a new community. The creator is automatically a member.
    """
    community = Community.from_orm(community_in, update={"created_by": current_user.id})
    community.members.append(current_user)
    new_community = await community_repo.create(session, obj_in=community)
    return new_community

@router.post("/{community_id}/join", status_code=status.HTTP_204_NO_CONTENT)
async def join_or_leave_community(
    community_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """
    Toggle membership in a community (join or leave).
    """
    community = await session.get(Community, community_id, options=[selectinload(Community.members)])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
        
    user_is_member = any(member.id == current_user.id for member in community.members)

    if user_is_member:
        community.members.remove(current_user)
    else:
        community.members.append(current_user)
    
    session.add(community)
    await session.commit()
    return

@router.get("/{community_id}/posts", response_model=List[PostPublic])
async def get_posts_in_community(
    community_id: str,
    session: AsyncSession = Depends(get_session),
    pagination: pagination_params = Depends(),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """
    Get the feed for a specific community.
    """
    statement = (
        select(Post)
        .where(Post.community_id == community_id)
        .options(selectinload(Post.author))
        .order_by(Post.created_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    result = await session.execute(statement)
    posts = result.scalars().all()
    return posts