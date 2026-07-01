from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from .user import _validate_password_strength


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: Optional[datetime] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class PasswordResetResponse(BaseModel):
    message: str


__all__ = [
    "Token",
    "TokenPayload",
    "UserLoginRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "PasswordResetResponse",
]
