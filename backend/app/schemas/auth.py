from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: Optional[datetime] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class PasswordResetResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None


__all__ = [
    "Token",
    "TokenPayload",
    "UserLoginRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "PasswordResetResponse",
]
