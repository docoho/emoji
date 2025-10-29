from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class EmojiBase(BaseModel):
    symbol: str = Field(min_length=1, max_length=8)
    title: str = Field(max_length=128)
    description: Optional[str] = Field(default=None, max_length=256)
    category: Optional[str] = Field(default=None, max_length=64)
    keywords: list[str] = Field(default_factory=list)


class EmojiCreate(EmojiBase):
    submitter_email: Optional[EmailStr] = None


class EmojiUpdate(BaseModel):
    symbol: Optional[str] = Field(default=None, min_length=1, max_length=8)
    title: Optional[str] = Field(default=None, max_length=128)
    description: Optional[str] = Field(default=None, max_length=256)
    category: Optional[str] = Field(default=None, max_length=64)
    keywords: Optional[list[str]] = None


class Emoji(EmojiBase):
    id: int
    submitter_email: Optional[EmailStr] = None
    can_delete: bool = False

    class Config:
        from_attributes = True


class EmojiListResponse(BaseModel):
    items: list[Emoji]
    total: int
    limit: int
    offset: int


__all__ = ["Emoji", "EmojiBase", "EmojiCreate", "EmojiUpdate", "EmojiListResponse"]
