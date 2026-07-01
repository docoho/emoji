from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import EmojiComment, EmojiLike, EmojiReport, EmojiSubmission, User
from app.schemas import EmojiReportItem


def normalize_keywords(keywords: list[str]) -> list[str]:
    return sorted({tag.strip() for tag in keywords if tag.strip()})


def load_like_counts(
    session: Session,
    emoji_ids: list[int],
    *,
    since: Optional[datetime] = None,
) -> dict[int, int]:
    if not emoji_ids:
        return {}

    query = (
        select(EmojiLike.emoji_id, func.count().label("cnt"))
        .where(EmojiLike.emoji_id.in_(emoji_ids))
        .group_by(EmojiLike.emoji_id)
    )
    if since is not None:
        query = query.where(EmojiLike.created_at >= since)
    rows = session.exec(query).all()
    return {row[0]: row[1] for row in rows}


def load_comment_counts(session: Session, emoji_ids: list[int]) -> dict[int, int]:
    if not emoji_ids:
        return {}

    rows = session.exec(
        select(EmojiComment.emoji_id, func.count().label("cnt"))
        .where(
            EmojiComment.emoji_id.in_(emoji_ids),
            EmojiComment.deleted_at.is_(None),
        )
        .group_by(EmojiComment.emoji_id)
    ).all()
    return {row[0]: row[1] for row in rows}


def load_submitter_names(session: Session, submissions: list[EmojiSubmission]) -> dict[int, str | None]:
    submitter_ids = {submission.submitter_id for submission in submissions if submission.submitter_id}
    if not submitter_ids:
        return {}

    rows = session.exec(select(User.id, User.display_name).where(col(User.id).in_(submitter_ids))).all()
    return {row[0]: row[1] for row in rows}


def load_liked_set(session: Session, current_user: Optional[User], emoji_ids: list[int]) -> set[int]:
    if current_user is None or not emoji_ids:
        return set()

    rows = session.exec(
        select(EmojiLike.emoji_id).where(
            EmojiLike.user_id == current_user.id,
            EmojiLike.emoji_id.in_(emoji_ids),
        )
    ).all()
    return set(rows)


def build_report_item(
    report: EmojiReport,
    *,
    emoji: EmojiSubmission,
    reporter: User,
    resolved_by: Optional[User],
) -> EmojiReportItem:
    return EmojiReportItem(
        id=report.id or 0,
        emoji_id=report.emoji_id,
        emoji_symbol=emoji.symbol,
        emoji_title=emoji.title,
        reporter_id=report.reporter_id,
        reporter_name=reporter.display_name,
        reporter_email=reporter.email,
        reason=report.reason,  # type: ignore[arg-type]
        details=report.details,
        status=report.status,  # type: ignore[arg-type]
        admin_note=report.admin_note,
        created_at=report.created_at,
        updated_at=report.updated_at,
        resolved_at=report.resolved_at,
        resolved_by_id=report.resolved_by_id,
        resolved_by_name=resolved_by.display_name if resolved_by is not None else None,
    )


__all__ = [
    "build_report_item",
    "load_comment_counts",
    "load_like_counts",
    "load_liked_set",
    "load_submitter_names",
    "normalize_keywords",
]
