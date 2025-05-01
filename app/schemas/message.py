from pydantic import BaseModel
from datetime import datetime


class MessageBase(BaseModel):
    sender_id: int
    receiver_id: int
    content: str
    timestamp: datetime
    is_read: bool

    class Config:
        from_attributes = True