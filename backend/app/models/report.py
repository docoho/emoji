from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class EmojiReport(SQLModel, table=True):
    __table_args__ = (
        Index("idx_emoji_report_emoji_status", "emoji_id", "status"),
        Index("idx_emoji_report_reporter_status", "reporter_id", "status"),
        Index("idx_emoji_report_status_created", "status", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    emoji_id: int = Field(foreign_key="emojisubmission.id", index=True, nullable=False)
    reporter_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    reason: str = Field(max_length=32, nullable=False)
    details: Optional[str] = Field(default=None, max_length=500)
    status: str = Field(default="open", max_length=32, nullable=False)
    admin_note: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )
    resolved_at: Optional[datetime] = Field(default=None)
    resolved_by_id: Optional[int] = Field(default=None, foreign_key="user.id")


__all__ = ["EmojiReport"]
