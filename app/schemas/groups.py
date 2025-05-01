from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None
    owner_id: int

class GroupCreate(GroupBase):
    pass

class GroupMessage(BaseModel):
    sender_id: int
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True

class GroupMemberAdd(BaseModel):
    user_id: int
    role: str = 'member'

class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    member_count: int
    your_role: str
    joined_at: datetime

    class Config:
        from_attributes = True    