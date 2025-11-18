from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class InstitutionPublic(BaseModel):
    id: str
    institution_name: str
    institution_description: Optional[str]
    institution_website: Optional[str]
    institution_location: Optional[str]
    institution_profile_picture: Optional[str]
    institution_email: Optional[str]

    # computed stats
    students_count: int | None = None
    posts_count: int | None = None

    model_config = ConfigDict(from_attributes=True)


class PostPublic(BaseModel):
    id: str
    author_id: str
    content: str
    post_type: str
    privacy: str
    school_scope: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstitutionTimelineResponse(BaseModel):
    """Response for student viewing their institution timeline."""
    institution: InstitutionPublic
    posts: List[PostPublic]

    model_config = ConfigDict(from_attributes=True)


class UploadedDocumentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    # either provide file_url directly or upload file (router supports UploadFile too)
    file_url: str

class UploadedDocumentPublic(BaseModel):
    id: str
    institution_id: str
    title: str
    description: Optional[str]
    file_url: str
    file_metadata: dict | None
    uploaded_by: Optional[str]
    is_processed: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)
