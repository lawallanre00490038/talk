# app/api/routers/comments.py
from fastapi import APIRouter, Depends, status,  HTTPException
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.db.models import User, Comment, Post
from app.schemas.auth import TokenUser
from app.schemas.post import CommentCreate
from app.db.repositories.comment_repo import comment_repo
from app.core.config import settings
from app.db.repositories.base import BaseRepository
from app.services.notification_service import notification_service, NotificationType
from app.api.deps import pagination_params

router = APIRouter()
post_repo = BaseRepository(Post)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_comment(
    *,
    session: AsyncSession = Depends(get_session),
    post_id: str,
    comment_in: CommentCreate,
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings))
):
    post = await post_repo.get(session, id=post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    comment = Comment.from_orm(
        comment_in,
        update={"author_id": current_user.id, "post_id": post_id}
    )
    new_comment = await comment_repo.create(session, obj_in=comment)
    
    # Create notification for the post author (if not the same user)
    if post.author_id != current_user.id:
        await notification_service.create_notification(
            session,
            user_id=post.author_id,
            notification_type=NotificationType.COMMENT,
            content={"message": f"{current_user.username} commented on your post.", "post_id": str(post_id)}
        )
    return new_comment


@router.get("/", response_model=List[Comment])
async def read_comments(
    *,
    session: AsyncSession = Depends(get_current_user_dependency(settings=settings)),
    post_id: str,
    pagination: pagination_params = Depends()
):
    comments = await comment_repo.get_comments_for_post(
        session, post_id=post_id, skip=pagination.skip, limit=pagination.limit
    )
    return comments