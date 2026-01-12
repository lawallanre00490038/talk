# app/schemas.py
import uuid
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from app.db.models import  PostType, PostPrivacy, MediaType, NotificationType
from app.schemas.auth import UserPublic
from enum import Enum


class PostBase(BaseModel):
    content: str
    privacy: PostPrivacy = PostPrivacy.PUBLIC
    is_school_scope: Optional[bool] = False
    post_type: Optional[PostType] = None

class PostCreate(PostBase):
    pass

class MediaCreate(BaseModel):
    media_type: MediaType
    url: str
    file_metadata: Optional[dict] = None  # match SQLModel field

class PostPublic(PostBase):
    id: str
    author_id: str
    post_type: PostType
    author: UserPublic
    media: List[MediaCreate] = []  # ensure default list
    model_config = ConfigDict(from_attributes=True)



class PresignedUrlResponse(BaseModel):
    upload_url: str
    file_key: str

class CommentCreate(BaseModel):
    content: str
    parent_comment_id: Optional[str] = None