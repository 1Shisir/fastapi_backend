from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class GroupBase(BaseModel):
    name: str
    owner_id: int

class GroupCreate(BaseModel):
    name: str
    member_ids: Optional[List[int]] = []

class GroupMessage(BaseModel):
    sender_id: int
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True

class GroupMemberAdd(BaseModel):
    user_ids: List[int]

class GroupResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime
    member_count: int
    members: List[int]

    class Config:
        from_attributes = True    

    