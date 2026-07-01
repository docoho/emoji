from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel, UniqueConstraint


class EmojiLike(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("user_id", "emoji_id"),
        Index("idx_emojilike_emoji_created", "emoji_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False)
    emoji_id: int = Field(foreign_key="emojisubmission.id", nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )


__all__ = ["EmojiLike"]
