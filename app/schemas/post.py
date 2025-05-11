from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PostBase(BaseModel):
    content: str
    image_url: Optional[str] = None
    image_public_id: Optional[str] = None
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

class PostOutWithUserLike(PostOut):
    is_liked_by_me: bool
    author_name: str

    class Config:
        from_attributes = True
