from typing import Optional
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


# --- Complaint Schemas ---
class ComplaintBase(BaseModel):
    reason: str
    reported_post_id: Optional[str] = None
    reported_comment_id: Optional[str] = None
    reported_user_id: Optional[str] = None

class ComplaintCreate(ComplaintBase):
    pass

class ComplaintPublic(ComplaintBase):
    id: str
    reporter_id: str
    is_resolved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)