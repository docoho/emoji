from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlmodel import Session, col, or_, select

from app.api.deps import get_current_active_superuser
from app.api.helpers import build_report_item
from app.core.emoji_moderation import (
    EMOJI_STATUS_APPROVED,
    EMOJI_STATUS_DRAFT,
    EMOJI_STATUS_PENDING,
    EMOJI_STATUS_REJECTED,
    normalize_moderation_reason,
)
from app.db import get_session
from app.models import Collection, EmojiComment, EmojiLike, EmojiReport, EmojiSubmission, User
from app.schemas import (
    AdminDashboardCategoryCount,
    AdminDashboardRecentEmoji,
    AdminDashboardRecentReport,
    AdminDashboardResponse,
    AdminDashboardStatusCount,
    AdminEmojiListResponse,
    AdminEmojiModerationUpdate,
    AdminEmojiQueueItem,
    EmojiModerationStatus,
    EmojiReportAdminUpdate,
    EmojiReportListResponse,
    EmojiReportStatus,
    EmojiReportItem,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _count(session: Session, statement) -> int:
    return int(session.exec(statement).one() or 0)


def _status_count_items(
    rows: list[tuple[str, int]],
    *,
    known_statuses: list[str],
) -> list[AdminDashboardStatusCount]:
    counts = {status_value: 0 for status_value in known_statuses}
    counts.update({row[0]: int(row[1]) for row in rows})
    return [
        AdminDashboardStatusCount(status=status_value, count=count)
        for status_value, count in counts.items()
    ]


@router.get("/dashboard", response_model=AdminDashboardResponse)
def get_admin_dashboard(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_superuser),
) -> AdminDashboardResponse:
    del current_user
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    emoji_status_rows = session.exec(
        select(EmojiSubmission.moderation_status, func.count().label("cnt")).group_by(
            EmojiSubmission.moderation_status
        )
    ).all()
    report_status_rows = session.exec(
        select(EmojiReport.status, func.count().label("cnt")).group_by(EmojiReport.status)
    ).all()

    emoji_status_counts = _status_count_items(
        emoji_status_rows,
        known_statuses=[
            EMOJI_STATUS_DRAFT,
            EMOJI_STATUS_PENDING,
            EMOJI_STATUS_APPROVED,
            EMOJI_STATUS_REJECTED,
        ],
    )
    report_status_counts = _status_count_items(
        report_status_rows,
        known_statuses=["open", "dismissed", "actioned"],
    )
    emoji_counts = {item.status: item.count for item in emoji_status_counts}
    report_counts = {item.status: item.count for item in report_status_counts}

    top_category_rows = session.exec(
        select(EmojiSubmission.category, func.count().label("cnt"))
        .where(
            EmojiSubmission.moderation_status == EMOJI_STATUS_APPROVED,
            EmojiSubmission.category.is_not(None),
            EmojiSubmission.category != "",
        )
        .group_by(EmojiSubmission.category)
        .order_by(func.count().desc(), EmojiSubmission.category.asc())
        .limit(5)
    ).all()
    top_categories = [
        AdminDashboardCategoryCount(category=row[0] or "Uncategorized", count=int(row[1]))
        for row in top_category_rows
    ]

    recent_pending = session.exec(
        select(EmojiSubmission)
        .where(EmojiSubmission.moderation_status == EMOJI_STATUS_PENDING)
        .order_by(EmojiSubmission.created_at.desc(), EmojiSubmission.id.desc())
        .limit(5)
    ).all()
    recent_reports = session.exec(
        select(EmojiReport)
        .where(EmojiReport.status == "open")
        .order_by(EmojiReport.created_at.desc(), EmojiReport.id.desc())
        .limit(5)
    ).all()

    related_user_ids = {
        user_id
        for user_id in [
            *(emoji.submitter_id for emoji in recent_pending),
            *(report.reporter_id for report in recent_reports),
        ]
        if user_id is not None
    }
    user_names: dict[int, Optional[str]] = {}
    if related_user_ids:
        user_rows = session.exec(select(User.id, User.display_name).where(User.id.in_(related_user_ids))).all()
        user_names = {row[0]: row[1] for row in user_rows}

    report_emoji_ids = {report.emoji_id for report in recent_reports}
    report_emojis = {}
    if report_emoji_ids:
        report_emojis = {
            emoji.id or 0: emoji
            for emoji in session.exec(
                select(EmojiSubmission).where(EmojiSubmission.id.in_(report_emoji_ids))
            ).all()
        }

    return AdminDashboardResponse(
        total_users=_count(session, select(func.count()).select_from(User)),
        active_users=_count(session, select(func.count()).select_from(User).where(User.is_active)),
        superuser_count=_count(
            session,
            select(func.count()).select_from(User).where(User.is_superuser),
        ),
        total_emojis=_count(session, select(func.count()).select_from(EmojiSubmission)),
        pending_emojis=emoji_counts.get(EMOJI_STATUS_PENDING, 0),
        approved_emojis=emoji_counts.get(EMOJI_STATUS_APPROVED, 0),
        rejected_emojis=emoji_counts.get(EMOJI_STATUS_REJECTED, 0),
        draft_emojis=emoji_counts.get(EMOJI_STATUS_DRAFT, 0),
        total_likes=_count(session, select(func.count()).select_from(EmojiLike)),
        total_comments=_count(
            session,
            select(func.count()).select_from(EmojiComment).where(EmojiComment.deleted_at.is_(None)),
        ),
        total_collections=_count(session, select(func.count()).select_from(Collection)),
        open_reports=report_counts.get("open", 0),
        dismissed_reports=report_counts.get("dismissed", 0),
        actioned_reports=report_counts.get("actioned", 0),
        new_users_7d=_count(
            session,
            select(func.count()).select_from(User).where(User.created_at >= seven_days_ago),
        ),
        new_emojis_7d=_count(
            session,
            select(func.count())
            .select_from(EmojiSubmission)
            .where(EmojiSubmission.created_at >= seven_days_ago),
        ),
        new_reports_7d=_count(
            session,
            select(func.count()).select_from(EmojiReport).where(EmojiReport.created_at >= seven_days_ago),
        ),
        emoji_status_counts=emoji_status_counts,
        report_status_counts=report_status_counts,
        top_categories=top_categories,
        recent_pending_emojis=[
            AdminDashboardRecentEmoji(
                id=emoji.id or 0,
                symbol=emoji.symbol,
                title=emoji.title,
                moderation_status=emoji.moderation_status,  # type: ignore[arg-type]
                created_at=emoji.created_at,
                submitter_id=emoji.submitter_id,
                submitter_name=user_names.get(emoji.submitter_id or 0),
            )
            for emoji in recent_pending
        ],
        recent_open_reports=[
            AdminDashboardRecentReport(
                id=report.id or 0,
                emoji_id=report.emoji_id,
                emoji_symbol=report_emojis[report.emoji_id].symbol,
                emoji_title=report_emojis[report.emoji_id].title,
                reason=report.reason,  # type: ignore[arg-type]
                status=report.status,  # type: ignore[arg-type]
                created_at=report.created_at,
                reporter_id=report.reporter_id,
                reporter_name=user_names.get(report.reporter_id),
            )
            for report in recent_reports
            if report.emoji_id in report_emojis
        ],
    )


def _build_admin_emoji_item(
    submission: EmojiSubmission,
    *,
    like_count: int,
    submitter_name: Optional[str],
    moderator_name: Optional[str],
) -> AdminEmojiQueueItem:
    return AdminEmojiQueueItem(
        id=submission.id or 0,
        symbol=submission.symbol,
        title=submission.title,
        description=submission.description,
        category=submission.category,
        keywords=submission.keyword_list,
        created_at=submission.created_at,
        like_count=like_count,
        submitter_id=submission.submitter_id,
        submitter_name=submitter_name,
        moderation_status=submission.moderation_status,  # type: ignore[arg-type]
        moderation_reason=submission.moderation_reason,
        moderated_at=submission.moderated_at,
        moderated_by_id=submission.moderated_by_id,
        moderated_by_name=moderator_name,
    )


@router.get("/emojis", response_model=AdminEmojiListResponse)
def list_admin_emojis(
    moderation_status: EmojiModerationStatus = Query(EMOJI_STATUS_PENDING, alias="status"),
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    submitter_id: Optional[int] = Query(default=None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_superuser),
) -> AdminEmojiListResponse:
    del current_user
    query = select(EmojiSubmission).where(EmojiSubmission.moderation_status == moderation_status)
    count_query = select(func.count()).select_from(EmojiSubmission).where(
        EmojiSubmission.moderation_status == moderation_status
    )

    if search:
        search_term = f"%{search.lower()}%"
        search_filter = or_(
            col(EmojiSubmission.title).ilike(search_term),
            col(EmojiSubmission.description).ilike(search_term),
            col(EmojiSubmission.keywords).ilike(search_term),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if category:
        query = query.where(EmojiSubmission.category == category)
        count_query = count_query.where(EmojiSubmission.category == category)

    if submitter_id is not None:
        query = query.where(EmojiSubmission.submitter_id == submitter_id)
        count_query = count_query.where(EmojiSubmission.submitter_id == submitter_id)

    total = int(session.exec(count_query).one())
    submissions = session.exec(
        query.order_by(EmojiSubmission.created_at.desc()).offset(offset).limit(limit)
    ).all()

    emoji_ids = [submission.id for submission in submissions if submission.id is not None]
    like_counts: dict[int, int] = {}
    if emoji_ids:
        count_rows = session.exec(
            select(EmojiLike.emoji_id, func.count().label("cnt"))
            .where(EmojiLike.emoji_id.in_(emoji_ids))
            .group_by(EmojiLike.emoji_id)
        ).all()
        like_counts = {row[0]: row[1] for row in count_rows}

    related_user_ids = {
        user_id
        for submission in submissions
        for user_id in (submission.submitter_id, submission.moderated_by_id)
        if user_id is not None
    }
    user_names: dict[int, Optional[str]] = {}
    if related_user_ids:
        user_rows = session.exec(select(User.id, User.display_name).where(User.id.in_(related_user_ids))).all()
        user_names = {row[0]: row[1] for row in user_rows}

    items = [
        _build_admin_emoji_item(
            submission,
            like_count=like_counts.get(submission.id or 0, 0),
            submitter_name=user_names.get(submission.submitter_id or 0),
            moderator_name=user_names.get(submission.moderated_by_id or 0),
        )
        for submission in submissions
    ]
    return AdminEmojiListResponse(items=items, total=total, limit=limit, offset=offset)


@router.patch("/emojis/{emoji_id}/moderation", response_model=AdminEmojiQueueItem)
def moderate_emoji(
    emoji_id: int,
    payload: AdminEmojiModerationUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_superuser),
) -> AdminEmojiQueueItem:
    submission = session.get(EmojiSubmission, emoji_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    submission.moderation_status = payload.status
    submission.moderated_by_id = current_user.id
    submission.moderated_at = datetime.now(timezone.utc)
    submission.moderation_reason = (
        normalize_moderation_reason(payload.reason)
        if payload.status == EMOJI_STATUS_REJECTED
        else None
    )

    session.add(submission)
    session.commit()
    session.refresh(submission)

    like_count = int(
        session.exec(
            select(func.count()).select_from(EmojiLike).where(EmojiLike.emoji_id == emoji_id)
        ).one()
    )
    return _build_admin_emoji_item(
        submission,
        like_count=like_count,
        submitter_name=session.exec(
            select(User.display_name).where(User.id == submission.submitter_id)
        ).first()
        if submission.submitter_id
        else None,
        moderator_name=current_user.display_name,
    )


@router.get("/reports", response_model=EmojiReportListResponse)
def list_admin_reports(
    report_status: EmojiReportStatus = Query("open", alias="status"),
    reason: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_superuser),
) -> EmojiReportListResponse:
    del current_user
    query = (
        select(EmojiReport)
        .join(EmojiSubmission, EmojiSubmission.id == EmojiReport.emoji_id)
        .join(User, User.id == EmojiReport.reporter_id)
        .where(EmojiReport.status == report_status)
    )
    count_query = (
        select(func.count())
        .select_from(EmojiReport)
        .join(EmojiSubmission, EmojiSubmission.id == EmojiReport.emoji_id)
        .join(User, User.id == EmojiReport.reporter_id)
        .where(EmojiReport.status == report_status)
    )

    if reason:
        query = query.where(EmojiReport.reason == reason)
        count_query = count_query.where(EmojiReport.reason == reason)

    if search:
        search_term = f"%{search.lower()}%"
        search_filter = or_(
            col(EmojiSubmission.title).ilike(search_term),
            col(User.display_name).ilike(search_term),
            col(User.email).ilike(search_term),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = int(session.exec(count_query).one())
    reports = session.exec(
        query.order_by(EmojiReport.created_at.desc(), EmojiReport.id.desc()).offset(offset).limit(limit)
    ).all()

    emoji_ids = {report.emoji_id for report in reports}
    reporter_ids = {report.reporter_id for report in reports}
    resolver_ids = {report.resolved_by_id for report in reports if report.resolved_by_id is not None}

    emojis = {
        emoji.id or 0: emoji
        for emoji in session.exec(select(EmojiSubmission).where(EmojiSubmission.id.in_(emoji_ids))).all()
    } if emoji_ids else {}
    users = {
        user.id or 0: user
        for user in session.exec(select(User).where(User.id.in_(reporter_ids | resolver_ids))).all()
    } if reporter_ids or resolver_ids else {}

    items = [
        build_report_item(
            report,
            emoji=emojis[report.emoji_id],
            reporter=users[report.reporter_id],
            resolved_by=users.get(report.resolved_by_id or 0),
        )
        for report in reports
    ]
    return EmojiReportListResponse(items=items, total=total, limit=limit, offset=offset)


@router.patch("/reports/{report_id}", response_model=EmojiReportItem)
def update_admin_report(
    report_id: int,
    payload: EmojiReportAdminUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_superuser),
) -> EmojiReportItem:
    report = session.get(EmojiReport, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    report.status = payload.status
    report.admin_note = normalize_moderation_reason(payload.admin_note)
    report.resolved_at = datetime.now(timezone.utc)
    report.resolved_by_id = current_user.id
    session.add(report)
    session.commit()
    session.refresh(report)

    emoji = session.get(EmojiSubmission, report.emoji_id)
    reporter = session.get(User, report.reporter_id)
    if emoji is None or reporter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report context not found")

    return build_report_item(report, emoji=emoji, reporter=reporter, resolved_by=current_user)


__all__ = ["router"]
