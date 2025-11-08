from typing import Dict, Any
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.db.models import NotificationType


# --- Notification Schemas ---
class NotificationPublic(BaseModel):
    id: str
    notification_type: NotificationType
    content: Dict[str, Any]
    is_read: bool
    created_at: datetime

    
    model_config = ConfigDict(from_attributes=True)