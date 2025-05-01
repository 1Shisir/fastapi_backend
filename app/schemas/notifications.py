from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class NotificationBase(BaseModel):
    message: str
    type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: int
    message: str
    type: str
    is_read: bool
    created_at: datetime  
    related_request_id: Optional[int] = None
    related_user_id: Optional[int] = None


    class Config:
        from_attributes = True

