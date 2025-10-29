from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class EmojiSubmission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(max_length=8, nullable=False)
    title: str = Field(max_length=128, nullable=False)
    description: Optional[str] = Field(default=None, max_length=256)
    category: Optional[str] = Field(default=None, max_length=64)
    keywords: str = Field(default="", max_length=512)
    submitter_email: Optional[str] = Field(default=None, max_length=256)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    submitter_id: Optional[int] = Field(default=None, foreign_key="user.id")

    @property
    def keyword_list(self) -> list[str]:
        return [word for word in self.keywords.split(",") if word]

    @keyword_list.setter
    def keyword_list(self, value: list[str]) -> None:
        self.keywords = ",".join(sorted({tag.strip() for tag in value if tag.strip()}))


__all__ = ["EmojiSubmission"]
