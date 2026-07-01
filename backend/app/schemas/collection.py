from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.emoji import Emoji


CollectionKind = Literal["public", "personal"]


class CollectionBase(BaseModel):
    name: str = Field(max_length=128)
    description: Optional[str] = Field(default=None, max_length=256)
    kind: CollectionKind = "personal"


class CollectionCreate(CollectionBase):
    slug: Optional[str] = Field(default=None, max_length=128)


class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    description: Optional[str] = Field(default=None, max_length=256)
    kind: Optional[CollectionKind] = None


class Collection(CollectionBase):
    id: int
    slug: str
    owner_id: int
    owner_name: Optional[str] = None
    emoji_count: int = 0
    contains_emoji: bool = False
    created_at: datetime
    updated_at: datetime
    emojis: list[Emoji] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CollectionListResponse(BaseModel):
    items: list[Collection]
    total: int
    limit: int
    offset: int


class EmojiCollectionsResponse(BaseModel):
    emoji_id: int
    selected_collection_ids: list[int] = Field(default_factory=list)
    collections: list[Collection] = Field(default_factory=list)


class CollectionEmojiAddRequest(BaseModel):
    emoji_id: int


class EmojiCollectionsUpdate(BaseModel):
    collection_ids: list[int] = Field(default_factory=list)


__all__ = [
    "Collection",
    "CollectionBase",
    "CollectionCreate",
    "CollectionKind",
    "CollectionListResponse",
    "CollectionUpdate",
    "CollectionEmojiAddRequest",
    "EmojiCollectionsResponse",
    "EmojiCollectionsUpdate",
]
