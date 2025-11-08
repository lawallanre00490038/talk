# app/schemas.py
import uuid
from pydantic import BaseModel, ConfigDict
from datetime import datetime

# --- Channel Schemas ---
class ChannelBase(BaseModel):
    name: str
    description: str
    is_private: bool = False

class ChannelCreate(ChannelBase):
    pass

class ChannelPublic(ChannelBase):
    id: str
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Community Schemas ---
class CommunityBase(BaseModel):
    name: str
    description: str

class CommunityCreate(CommunityBase):
    pass

class CommunityPublic(CommunityBase):
    id: str
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
