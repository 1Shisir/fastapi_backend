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
    user_id: int | None = None
    profile_public_id: Optional[str] = None

    class Config:
        from_attributes = True          


class UserInfoUpdateByAdmin(BaseModel):
    is_verified: bool | None = False
    
    class Config:
        from_attributes = True


