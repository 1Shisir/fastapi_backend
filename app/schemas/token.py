from pydantic import BaseModel,EmailStr
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role:str
    user_id:int


class TokenData(BaseModel):
    email: Optional[EmailStr] = None