from pydantic import BaseModel, EmailStr
from app.schemas.user_info import UserInfo
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str
    role: str = "user"

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: EmailStr
    password: str

    
class UserOut(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    profile_picture: Optional[str] = None

    class Config:
        from_attributes = True

class UnverifiedUserInfoResponse(UserOut):
    profile_picture:Optional [str] = None
    is_verified: Optional[bool] = False

    class Config:
        from_attributes = True