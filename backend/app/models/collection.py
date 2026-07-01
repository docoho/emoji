from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class Collection(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("owner_id", "slug"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    slug: str = Field(index=True, max_length=128, nullable=False)
    name: str = Field(max_length=128, nullable=False)
    description: Optional[str] = Field(default=None, max_length=256)
    kind: str = Field(default="personal", max_length=16, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


class CollectionEmoji(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("collection_id", "emoji_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: int = Field(foreign_key="collection.id", index=True, nullable=False)
    emoji_id: int = Field(foreign_key="emojisubmission.id", index=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )


__all__ = ["Collection", "CollectionEmoji"]
