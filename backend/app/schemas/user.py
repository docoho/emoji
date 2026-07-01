from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.collection import Collection
from app.schemas.emoji import Emoji


class UserBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = Field(default=None, max_length=128)


def _validate_password_strength(password: str) -> str:
    """Shared password strength validator."""
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit")
    return password


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserPublic(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    email_verified: bool
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    oauth_provider: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileStats(BaseModel):
    emoji_count: int = 0
    total_likes_received: int = 0
    collection_count: int = 0
    public_collection_count: int = 0
    categories_used_count: int = 0


class UserProfileAchievement(BaseModel):
    id: str
    title: str
    description: str
    icon_key: str
    earned: bool = False
    progress_current: int = 0
    progress_target: int = 0


class UserProfileHighlights(BaseModel):
    top_emoji: Optional[Emoji] = None
    recent_public_collections: list[Collection] = Field(default_factory=list)


class UserProfile(BaseModel):
    id: int
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    emoji_count: int = 0
    total_likes_received: int = 0
    collection_count: int = 0
    emojis: list[Emoji] = Field(default_factory=list)
    collections: list[Collection] = Field(default_factory=list)
    stats: UserProfileStats = Field(default_factory=UserProfileStats)
    achievements: list[UserProfileAchievement] = Field(default_factory=list)
    highlights: UserProfileHighlights = Field(default_factory=UserProfileHighlights)


class UserMeUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=128)
    avatar_url: Optional[str] = Field(default=None, max_length=512)
    bio: Optional[str] = Field(default=None, max_length=280)

    @field_validator("display_name", "bio")
    @classmethod
    def blank_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            return None
        if not cleaned.startswith(("https://", "http://")):
            raise ValueError("avatar_url must be an http or https URL")
        return cleaned


__all__ = [
    "UserCreate",
    "UserMeUpdate",
    "UserProfile",
    "UserProfileAchievement",
    "UserProfileHighlights",
    "UserProfileStats",
    "UserPublic",
]
