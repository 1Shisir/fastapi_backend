from pydantic import BaseModel
from datetime import datetime

class PostBase(BaseModel):
    content: str
    likes_count: int = 0

class PostCreate(PostBase):
    pass

class PostOut(PostBase):
    id: int
    user_id: int
    created_at: datetime
    likes_count: int

    class Config:
        from_attributes = True
