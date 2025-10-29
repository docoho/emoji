from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: Optional[datetime] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


__all__ = ["Token", "TokenPayload", "UserLoginRequest"]
