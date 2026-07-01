from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: Optional[str] = Field(default=None)
    google_id: Optional[str] = Field(default=None, unique=True, index=True)
    oauth_provider: Optional[str] = Field(default=None)
    email_verified: bool = Field(default=False)
    avatar_url: Optional[str] = Field(default=None)
    display_name: Optional[str] = Field(default=None, max_length=128)
    bio: Optional[str] = Field(default=None, max_length=280)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    token_version: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


__all__ = ["User"]
