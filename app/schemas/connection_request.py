from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class ConnectionRequestBase(BaseModel):
    sender_id: int
    receiver_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class FriendResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    profile_picture:Optional[str] = None

    class Config:
        from_attributes = True        