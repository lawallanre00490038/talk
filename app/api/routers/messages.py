from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.core.config import settings
from app.db.models import Conversation, ConversationUserLink, Message, User
from app.schemas.messages import ConversationCreate, ConversationPublic, MessageCreate, MessagePublic
from app.schemas.auth import TokenUser
from app.db.repositories.base import BaseRepository

router = APIRouter()
conversation_repo = BaseRepository(Conversation)
message_repo = BaseRepository(Message)


@router.post("/", response_model=ConversationPublic, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_in: ConversationCreate,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """Create a new conversation and add members."""
    conv = Conversation(title=conversation_in.title, is_group=conversation_in.is_group, created_by=current_user.id)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)

    # Add current user as member
    link = ConversationUserLink(user_id=current_user.id, conversation_id=conv.id)
    session.add(link)

    # Add additional members if provided
    if conversation_in.member_ids:
        for uid in conversation_in.member_ids:
            # skip if trying to add self again
            if uid == current_user.id:
                continue
            user = await session.get(User, uid)
            if user:
                session.add(ConversationUserLink(user_id=uid, conversation_id=conv.id))

    await session.commit()
    await session.refresh(conv)
    return conv


@router.get("/me", response_model=List[ConversationPublic])
async def get_my_conversations(
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    stmt = (
        select(Conversation)
        .join(ConversationUserLink, Conversation.id == ConversationUserLink.conversation_id)
        .where(ConversationUserLink.user_id == current_user.id)
        .options(selectinload(Conversation.members), selectinload(Conversation.messages))
        .order_by(Conversation.created_at.desc())
    )
    result = await session.execute(stmt)
    convs = result.scalars().all()
    return convs


@router.post("/{conversation_id}/messages", response_model=MessagePublic, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: str,
    message_in: MessageCreate,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    # Ensure conversation exists and user is a member
    stmt = select(ConversationUserLink).where(ConversationUserLink.conversation_id == conversation_id, ConversationUserLink.user_id == current_user.id)
    res = await session.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this conversation")

    msg = Message(conversation_id=conversation_id, sender_id=current_user.id, content=message_in.content, attachments=message_in.attachments or {})
    new_msg = await message_repo.create(session, obj_in=msg)
    return new_msg


@router.get("/{conversation_id}/messages", response_model=List[MessagePublic])
async def get_messages(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
    limit: int = 50,
    offset: int = 0,
):
    # Ensure membership
    stmt_check = select(ConversationUserLink).where(ConversationUserLink.conversation_id == conversation_id, ConversationUserLink.user_id == current_user.id)
    res_check = await session.execute(stmt_check)
    if not res_check.scalars().first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this conversation")

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .options(selectinload(Message.sender))
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    messages = result.scalars().all()
    return list(reversed(messages))  # return chronological order
