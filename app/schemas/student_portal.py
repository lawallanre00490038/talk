from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class StudentResourceCreate(BaseModel):
    institution_id: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    resource_type: Optional[str] = None

class StudentResourcePublic(BaseModel):
    id: str
    institution_id: str
    title: str
    description: Optional[str]
    url: Optional[str]
    resource_type: Optional[str]
    created_by: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
