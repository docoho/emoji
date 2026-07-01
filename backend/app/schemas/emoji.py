from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

EmojiModerationStatus = Literal["draft", "pending", "approved", "rejected"]
CreatorEmojiIntent = Literal["draft", "submit"]
EmojiReportReason = Literal["spam", "copyright", "offensive", "misleading", "other"]
EmojiReportStatus = Literal["open", "dismissed", "actioned"]


class EmojiBase(BaseModel):
    symbol: str = Field(min_length=1, max_length=8)
    title: str = Field(max_length=128)
    description: Optional[str] = Field(default=None, max_length=256)
    category: Optional[str] = Field(default=None, max_length=64)
    keywords: list[str] = Field(default_factory=list)


class EmojiCreate(EmojiBase):
    pass


class CreatorEmojiCreate(EmojiBase):
    intent: CreatorEmojiIntent = "submit"


class EmojiUpdate(BaseModel):
    symbol: Optional[str] = Field(default=None, min_length=1, max_length=8)
    title: Optional[str] = Field(default=None, max_length=128)
    description: Optional[str] = Field(default=None, max_length=256)
    category: Optional[str] = Field(default=None, max_length=64)
    keywords: Optional[list[str]] = None


class Emoji(EmojiBase):
    id: int
    can_delete: bool = False
    like_count: int = 0
    comment_count: int = 0
    is_liked: bool = False
    created_at: Optional[datetime] = None
    submitter_id: Optional[int] = None
    submitter_name: Optional[str] = None
    moderation_status: EmojiModerationStatus = "pending"
    moderation_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EmojiListResponse(BaseModel):
    items: list[Emoji]
    total: int
    limit: int
    offset: int


class CreatorEmojiListResponse(BaseModel):
    items: list[Emoji]
    total: int
    limit: int
    offset: int


class CreatorAnalyticsResponse(BaseModel):
    draft_count: int = 0
    pending_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    total_likes_received: int = 0
    top_emojis: list[Emoji] = Field(default_factory=list)


class AdminEmojiModerationUpdate(BaseModel):
    status: Literal["approved", "rejected"]
    reason: Optional[str] = Field(default=None, max_length=512)


class AdminEmojiQueueItem(EmojiBase):
    id: int
    created_at: datetime
    like_count: int = 0
    submitter_id: Optional[int] = None
    submitter_name: Optional[str] = None
    moderation_status: EmojiModerationStatus
    moderation_reason: Optional[str] = None
    moderated_at: Optional[datetime] = None
    moderated_by_id: Optional[int] = None
    moderated_by_name: Optional[str] = None


class AdminEmojiListResponse(BaseModel):
    items: list[AdminEmojiQueueItem]
    total: int
    limit: int
    offset: int


class AdminDashboardStatusCount(BaseModel):
    status: str
    count: int


class AdminDashboardCategoryCount(BaseModel):
    category: str
    count: int


class AdminDashboardRecentEmoji(BaseModel):
    id: int
    symbol: str
    title: str
    moderation_status: EmojiModerationStatus
    created_at: datetime
    submitter_id: Optional[int] = None
    submitter_name: Optional[str] = None


class AdminDashboardRecentReport(BaseModel):
    id: int
    emoji_id: int
    emoji_symbol: str
    emoji_title: str
    reason: EmojiReportReason
    status: EmojiReportStatus
    created_at: datetime
    reporter_id: int
    reporter_name: Optional[str] = None


class AdminDashboardResponse(BaseModel):
    total_users: int = 0
    active_users: int = 0
    superuser_count: int = 0
    total_emojis: int = 0
    pending_emojis: int = 0
    approved_emojis: int = 0
    rejected_emojis: int = 0
    draft_emojis: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_collections: int = 0
    open_reports: int = 0
    dismissed_reports: int = 0
    actioned_reports: int = 0
    new_users_7d: int = 0
    new_emojis_7d: int = 0
    new_reports_7d: int = 0
    emoji_status_counts: list[AdminDashboardStatusCount] = Field(default_factory=list)
    report_status_counts: list[AdminDashboardStatusCount] = Field(default_factory=list)
    top_categories: list[AdminDashboardCategoryCount] = Field(default_factory=list)
    recent_pending_emojis: list[AdminDashboardRecentEmoji] = Field(default_factory=list)
    recent_open_reports: list[AdminDashboardRecentReport] = Field(default_factory=list)


class EmojiReportCreate(BaseModel):
    reason: EmojiReportReason
    details: Optional[str] = Field(default=None, max_length=500)


class EmojiReportAdminUpdate(BaseModel):
    status: Literal["dismissed", "actioned"]
    admin_note: Optional[str] = Field(default=None, max_length=500)


class EmojiReportItem(BaseModel):
    id: int
    emoji_id: int
    emoji_symbol: str
    emoji_title: str
    reporter_id: int
    reporter_name: Optional[str] = None
    reporter_email: Optional[str] = None
    reason: EmojiReportReason
    details: Optional[str] = None
    status: EmojiReportStatus
    admin_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_id: Optional[int] = None
    resolved_by_name: Optional[str] = None


class EmojiReportListResponse(BaseModel):
    items: list[EmojiReportItem]
    total: int
    limit: int
    offset: int


class EmojiCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=500)


class EmojiCommentItem(BaseModel):
    id: int
    emoji_id: int
    body: str
    created_at: datetime
    updated_at: datetime
    author_id: int
    author_name: Optional[str] = None
    author_avatar_url: Optional[str] = None
    can_delete: bool = False


class EmojiCommentListResponse(BaseModel):
    items: list[EmojiCommentItem]
    total: int
    limit: int
    offset: int


__all__ = [
    "AdminEmojiListResponse",
    "AdminEmojiModerationUpdate",
    "AdminEmojiQueueItem",
    "AdminDashboardCategoryCount",
    "AdminDashboardRecentEmoji",
    "AdminDashboardRecentReport",
    "AdminDashboardResponse",
    "AdminDashboardStatusCount",
    "CreatorAnalyticsResponse",
    "CreatorEmojiCreate",
    "CreatorEmojiIntent",
    "CreatorEmojiListResponse",
    "EmojiCommentCreate",
    "EmojiCommentItem",
    "EmojiCommentListResponse",
    "Emoji",
    "EmojiBase",
    "EmojiCreate",
    "EmojiListResponse",
    "EmojiModerationStatus",
    "EmojiReportAdminUpdate",
    "EmojiReportCreate",
    "EmojiReportItem",
    "EmojiReportListResponse",
    "EmojiReportReason",
    "EmojiReportStatus",
    "EmojiUpdate",
]
