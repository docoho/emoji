from __future__ import annotations

from typing import Any, Optional

from app.models import EmojiSubmission

EMOJI_STATUS_DRAFT = "draft"
EMOJI_STATUS_PENDING = "pending"
EMOJI_STATUS_APPROVED = "approved"
EMOJI_STATUS_REJECTED = "rejected"
EMOJI_MODERATION_STATUSES = (
    EMOJI_STATUS_DRAFT,
    EMOJI_STATUS_PENDING,
    EMOJI_STATUS_APPROVED,
    EMOJI_STATUS_REJECTED,
)

# Fields whose modification on an APPROVED emoji must trigger re-moderation.
# Matches every user-visible content field exposed by EmojiUpdate.
RE_MODERATION_TRIGGER_FIELDS = ("symbol", "title", "description", "category", "keywords")


def apply_public_emoji_filter(statement):
    return statement.where(EmojiSubmission.moderation_status == EMOJI_STATUS_APPROVED)


def normalize_moderation_reason(reason: Optional[str]) -> Optional[str]:
    if reason is None:
        return None
    cleaned = reason.strip()
    return cleaned or None


def is_public_emoji(submission: Optional[EmojiSubmission]) -> bool:
    return bool(submission is not None and submission.moderation_status == EMOJI_STATUS_APPROVED)


def reset_moderation_on_edit(submission: EmojiSubmission, payload: Any) -> bool:
    """Send an APPROVED submission back to PENDING when content is edited.

    Returns True if a reset was applied, False otherwise. Only fires when the
    submission is currently APPROVED and the payload supplies at least one
    user-visible field. Clearing the moderated_* fields ensures the queue UI
    shows a fresh entry for re-review.
    """
    if submission.moderation_status != EMOJI_STATUS_APPROVED:
        return False
    if not any(getattr(payload, field, None) is not None for field in RE_MODERATION_TRIGGER_FIELDS):
        return False
    submission.moderation_status = EMOJI_STATUS_PENDING
    submission.moderation_reason = None
    submission.moderated_at = None
    submission.moderated_by_id = None
    return True


__all__ = [
    "EMOJI_MODERATION_STATUSES",
    "EMOJI_STATUS_APPROVED",
    "EMOJI_STATUS_DRAFT",
    "EMOJI_STATUS_PENDING",
    "EMOJI_STATUS_REJECTED",
    "RE_MODERATION_TRIGGER_FIELDS",
    "apply_public_emoji_filter",
    "is_public_emoji",
    "normalize_moderation_reason",
    "reset_moderation_on_edit",
]
