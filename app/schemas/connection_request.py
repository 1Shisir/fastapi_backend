from datetime import datetime
from pydantic import BaseModel

class ConnectionRequestBase(BaseModel):
    sender_id: int
    receiver_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class FriendResponse(BaseModel):
    email: str
    first_name: str
    last_name: str
    profile_picture: str
    created_at: datetime

    class Config:
        from_attributes = True        