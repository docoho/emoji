from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class EmojiComment(SQLModel, table=True):
    __table_args__ = (
        Index("idx_emoji_comment_emoji_deleted", "emoji_id", "deleted_at"),
        Index("idx_emoji_comment_author_deleted", "author_id", "deleted_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    emoji_id: int = Field(foreign_key="emojisubmission.id", index=True, nullable=False)
    author_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    body: str = Field(max_length=500, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )
    deleted_at: Optional[datetime] = Field(default=None)


__all__ = ["EmojiComment"]
