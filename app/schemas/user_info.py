from pydantic import BaseModel
from datetime import date
from typing import Optional


class UserInfoCreate(BaseModel):
    user_id: int
    address: Optional[str] = None
    phone_number: Optional[str] = None
    dob: Optional[date] = None  # Use str for date representation
    passions: Optional[str] = None
    is_verified: bool  = False
    lifestyle: Optional[str] = None
    dietary: Optional[str] = None
    available: bool = False
    religion: Optional[str] = None
    number_of_children: Optional[int] = 0
    profile_picture: Optional[str] = None
    profile_public_id: Optional[str] = None

    class Config:
        from_attributes = True

class UserInfoResponse(BaseModel):
    id: int
    user_id: int | None = None
    address: str | None = None
    phone_number: str | None = None
    dob: date | None = None  # Use str for date representation
    passions: str | None = None
    is_verified: bool | None =False
    lifestyle: str | None = None
    dietary: str | None = None
    available: bool | None = False
    religion: str | None = None
    number_of_children: Optional[int] = 0
    profile_picture: Optional[str] | None = None
    profile_public_id: Optional[str] = None

    class Config:
        from_attributes = True          

class UserInfoUpdate(BaseModel):
    address:Optional[str] = None
    phone_number: Optional[str] = None
    dob: Optional[date] = None  # Use str for date representation
    passions: Optional[str] = None
    lifestyle: Optional[str] = None
    dietary: Optional[str] = None
    available: Optional[bool] = None
    religion: Optional[str] = None
    number_of_children: Optional[int] = None

    class Config:
        from_attributes = True
    

class UserInfoUpdateByAdmin(BaseModel):
    is_verified: bool | None = False
    
    class Config:
        from_attributes = True


