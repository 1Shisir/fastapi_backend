from pydantic import BaseModel,EmailStr
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[EmailStr] = None