# app/schemas.py
import uuid
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from app.db.models import  PostType, PostPrivacy, MediaType, NotificationType
from app.schemas.auth import UserPublic
from enum import Enum


class PostBase(BaseModel):
    content: str
    privacy: PostPrivacy = PostPrivacy.PUBLIC
    school_scope:  Optional[str] = None

class PostCreate(PostBase):
    pass

class MediaMetadata(BaseModel):
    duration: Optional[float] = None
    cover_image_url: Optional[str] = None

class MediaCreate(BaseModel):
    media_type: MediaType
    url: str
    metadata: Optional[MediaMetadata] = None

class PostPublic(PostBase):
    id: str
    author_id: str
    post_type: PostType
    author: UserPublic
    # media: List[MediaCreate] # Simplified for response

    model_config = ConfigDict(from_attributes=True)

class PresignedUrlResponse(BaseModel):
    upload_url: str
    file_key: str

class CommentCreate(BaseModel):
    content: str
    parent_comment_id: Optional[str] = None