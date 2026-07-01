from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, or_
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.api.helpers import load_comment_counts, load_like_counts, normalize_keywords
from app.core.emoji_moderation import (
    EMOJI_MODERATION_STATUSES,
    EMOJI_STATUS_APPROVED,
    EMOJI_STATUS_DRAFT,
    EMOJI_STATUS_PENDING,
    EMOJI_STATUS_REJECTED,
    reset_moderation_on_edit,
)
from app.core.ratelimit import content_create_limiter
from app.db import get_session
from app.models import EmojiLike, EmojiSubmission, User
from app.schemas import (
    CreatorAnalyticsResponse,
    CreatorEmojiCreate,
    CreatorEmojiListResponse,
    Emoji,
    EmojiModerationStatus,
    EmojiUpdate,
)

router = APIRouter(prefix="/creator", tags=["creator"])


def _owner_clause(current_user: User):
    return or_(
        EmojiSubmission.submitter_id == current_user.id,
        and_(
            EmojiSubmission.submitter_id.is_(None),
            EmojiSubmission.submitter_email == current_user.email,
        ),
    )


def _find_duplicate(
    session: Session,
    *,
    symbol: str,
    title: str,
    exclude_id: Optional[int] = None,
) -> Optional[EmojiSubmission]:
    query = select(EmojiSubmission).where(
        EmojiSubmission.symbol == symbol,
        EmojiSubmission.title == title,
    )
    if exclude_id is not None:
        query = query.where(EmojiSubmission.id != exclude_id)
    return session.exec(query).first()


def _get_owned_submission_or_404(
    session: Session,
    emoji_id: int,
    current_user: User,
) -> EmojiSubmission:
    submission = session.exec(
        select(EmojiSubmission).where(
            EmojiSubmission.id == emoji_id,
            _owner_clause(current_user),
        )
    ).first()
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")
    return submission


def _build_emoji(
    submission: EmojiSubmission,
    *,
    current_user: User,
    like_count: int = 0,
    comment_count: int = 0,
) -> Emoji:
    can_delete = False
    if submission.submitter_id == current_user.id:
        can_delete = True
    elif submission.submitter_id is None and submission.submitter_email == current_user.email:
        can_delete = True

    return Emoji(
        id=submission.id or 0,
        symbol=submission.symbol,
        title=submission.title,
        description=submission.description,
        category=submission.category,
        keywords=submission.keyword_list,
        can_delete=can_delete,
        like_count=like_count,
        comment_count=comment_count,
        is_liked=False,
        created_at=submission.created_at,
        submitter_id=submission.submitter_id,
        submitter_name=current_user.display_name,
        moderation_status=submission.moderation_status,  # type: ignore[arg-type]
        moderation_reason=submission.moderation_reason,
    )


def _next_duplicate_title(session: Session, *, symbol: str, title: str) -> str:
    first_copy = f"{title} (Copy)"
    if _find_duplicate(session, symbol=symbol, title=first_copy) is None:
        return first_copy

    suffix = 2
    while True:
        candidate = f"{title} (Copy {suffix})"
        if _find_duplicate(session, symbol=symbol, title=candidate) is None:
            return candidate
        suffix += 1


@router.get("/emojis", response_model=CreatorEmojiListResponse)
def list_creator_emojis(
    status_filter: Optional[EmojiModerationStatus] = Query(default=None, alias="status"),
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CreatorEmojiListResponse:
    if status_filter is not None and status_filter not in EMOJI_MODERATION_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid emoji status")

    base_query = select(EmojiSubmission).where(_owner_clause(current_user))
    if status_filter is not None:
        base_query = base_query.where(EmojiSubmission.moderation_status == status_filter)

    count_query = select(func.count()).select_from(EmojiSubmission).where(_owner_clause(current_user))
    if status_filter is not None:
        count_query = count_query.where(EmojiSubmission.moderation_status == status_filter)
    total = int(session.exec(count_query).one())

    query = base_query.order_by(EmojiSubmission.created_at.desc(), EmojiSubmission.id.desc())
    submissions = session.exec(query.offset(offset).limit(limit)).all()
    emoji_ids = [submission.id for submission in submissions if submission.id is not None]
    like_counts = load_like_counts(session, emoji_ids)
    comment_counts = load_comment_counts(session, emoji_ids)
    items = [
        _build_emoji(
            submission,
            current_user=current_user,
            like_count=like_counts.get(submission.id or 0, 0),
            comment_count=comment_counts.get(submission.id or 0, 0),
        )
        for submission in submissions
    ]
    return CreatorEmojiListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/emojis", response_model=Emoji, status_code=status.HTTP_201_CREATED)
def create_creator_emoji(
    payload: CreatorEmojiCreate,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Emoji:
    content_create_limiter.check(request)
    if _find_duplicate(session, symbol=payload.symbol, title=payload.title) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Emoji already exists")

    submission = EmojiSubmission(
        symbol=payload.symbol,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        submitter_email=current_user.email,
        submitter_id=current_user.id,
        moderation_status=EMOJI_STATUS_DRAFT if payload.intent == "draft" else EMOJI_STATUS_PENDING,
    )
    submission.keyword_list = normalize_keywords(payload.keywords)
    session.add(submission)
    session.commit()
    session.refresh(submission)
    return _build_emoji(submission, current_user=current_user)


@router.put("/emojis/{emoji_id}", response_model=Emoji)
def update_creator_emoji(
    emoji_id: int,
    payload: EmojiUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Emoji:
    submission = _get_owned_submission_or_404(session, emoji_id, current_user)
    next_symbol = payload.symbol if payload.symbol is not None else submission.symbol
    next_title = payload.title if payload.title is not None else submission.title
    if _find_duplicate(session, symbol=next_symbol, title=next_title, exclude_id=emoji_id) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Emoji already exists")

    reset_moderation_on_edit(submission, payload)

    if payload.symbol is not None:
        submission.symbol = payload.symbol
    if payload.title is not None:
        submission.title = payload.title
    if payload.description is not None:
        submission.description = payload.description
    if payload.category is not None:
        submission.category = payload.category
    if payload.keywords is not None:
        submission.keyword_list = normalize_keywords(payload.keywords)

    session.add(submission)
    session.commit()
    session.refresh(submission)
    like_counts = load_like_counts(session, [emoji_id])
    comment_counts = load_comment_counts(session, [emoji_id])
    return _build_emoji(
        submission,
        current_user=current_user,
        like_count=like_counts.get(emoji_id, 0),
        comment_count=comment_counts.get(emoji_id, 0),
    )


@router.post("/emojis/{emoji_id}/submit", response_model=Emoji)
def submit_creator_emoji(
    emoji_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Emoji:
    submission = _get_owned_submission_or_404(session, emoji_id, current_user)
    if submission.moderation_status not in (EMOJI_STATUS_DRAFT, EMOJI_STATUS_REJECTED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only drafts or rejected emojis can be submitted",
        )

    submission.moderation_status = EMOJI_STATUS_PENDING
    submission.moderation_reason = None
    submission.moderated_at = None
    submission.moderated_by_id = None
    session.add(submission)
    session.commit()
    session.refresh(submission)
    return _build_emoji(submission, current_user=current_user)


@router.post("/emojis/{emoji_id}/duplicate", response_model=Emoji, status_code=status.HTTP_201_CREATED)
def duplicate_creator_emoji(
    emoji_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Emoji:
    content_create_limiter.check(request)
    source = _get_owned_submission_or_404(session, emoji_id, current_user)

    duplicate = EmojiSubmission(
        symbol=source.symbol,
        title=_next_duplicate_title(session, symbol=source.symbol, title=source.title),
        description=source.description,
        category=source.category,
        submitter_email=current_user.email,
        submitter_id=current_user.id,
        moderation_status=EMOJI_STATUS_DRAFT,
    )
    duplicate.keyword_list = list(source.keyword_list)
    session.add(duplicate)
    session.commit()
    session.refresh(duplicate)
    return _build_emoji(duplicate, current_user=current_user)


@router.get("/analytics", response_model=CreatorAnalyticsResponse)
def get_creator_analytics(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CreatorAnalyticsResponse:
    owner = _owner_clause(current_user)

    status_rows = session.exec(
        select(EmojiSubmission.moderation_status, func.count())
        .where(owner)
        .group_by(EmojiSubmission.moderation_status)
    ).all()
    counts = {row[0]: row[1] for row in status_rows}

    like_sq = (
        select(EmojiLike.emoji_id, func.count().label("cnt"))
        .group_by(EmojiLike.emoji_id)
        .subquery()
    )
    total_likes = int(session.exec(
        select(func.coalesce(func.sum(like_sq.c.cnt), 0))
        .select_from(EmojiSubmission)
        .outerjoin(like_sq, EmojiSubmission.id == like_sq.c.emoji_id)
        .where(owner, EmojiSubmission.moderation_status == EMOJI_STATUS_APPROVED)
    ).one())

    top_submissions = session.exec(
        select(EmojiSubmission)
        .outerjoin(like_sq, EmojiSubmission.id == like_sq.c.emoji_id)
        .where(owner, EmojiSubmission.moderation_status == EMOJI_STATUS_APPROVED)
        .order_by(
            func.coalesce(like_sq.c.cnt, 0).desc(),
            EmojiSubmission.created_at.desc(),
            EmojiSubmission.id.desc(),
        )
        .limit(3)
    ).all()

    top_ids = [s.id for s in top_submissions if s.id is not None]
    top_like_counts = load_like_counts(session, top_ids)
    top_comment_counts = load_comment_counts(session, top_ids)

    return CreatorAnalyticsResponse(
        draft_count=counts.get(EMOJI_STATUS_DRAFT, 0),
        pending_count=counts.get(EMOJI_STATUS_PENDING, 0),
        approved_count=counts.get(EMOJI_STATUS_APPROVED, 0),
        rejected_count=counts.get(EMOJI_STATUS_REJECTED, 0),
        total_likes_received=total_likes,
        top_emojis=[
            _build_emoji(
                s,
                current_user=current_user,
                like_count=top_like_counts.get(s.id or 0, 0),
                comment_count=top_comment_counts.get(s.id or 0, 0),
            )
            for s in top_submissions
        ],
    )


__all__ = ["router"]
