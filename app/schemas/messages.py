from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict

class ConversationCreate(BaseModel):
    title: Optional[str] = None
    is_group: bool = False
    member_ids: Optional[List[str]] = None

class ConversationPublic(BaseModel):
    id: str
    title: Optional[str]
    is_group: bool
    created_by: Optional[str]
    created_at: str

    model_config = ConfigDict(from_attributes=True)

class MessageCreate(BaseModel):
    content: str
    attachments: Optional[Dict[str, str]] = None

class MessagePublic(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    content: str
    attachments: Optional[Dict[str, str]] = None
    is_read: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)
