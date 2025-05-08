from pydantic import BaseModel
from datetime import date
from typing import Optional


class UserInfo(BaseModel):
    id: int
    address: str | None = None
    phone_number: str | None = None
    dob: date | None = None  # Use str for date representation
    passions: str | None = None
    is_verified: bool | None = False
    lifestyle: str | None = None
    dietary: str | None = None
    available: bool | None = None
    religion: str | None = None
    number_of_children: int | None = None
    profile_picture: str | None = None
    profile_public_id: Optional[str] = None

    class Config:
        from_attributes = True

class UserInfoCreate(BaseModel):
    address: str | None = None
    phone_number: str | None = None
    dob: date | None = None  # Use str for date representation
    passions: str | None = None
    lifestyle: str | None = None
    dietary: str | None = None
    available: bool | None = None
    religion: str | None = None
    number_of_children: int | None = None   

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
    number_of_children: int | None = None
    profile_picture: str | None = None
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
    profile_picture: Optional[str] = None
    profile_public_id: Optional[str] = None

    class Config:
        from_attributes = True
    

class UserInfoUpdateByAdmin(BaseModel):
    is_verified: bool | None = False
    
    class Config:
        from_attributes = True


