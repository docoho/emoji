from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, delete, or_, select

from app.api.deps import get_current_user, get_optional_user
from app.api.helpers import build_report_item, load_comment_counts, load_like_counts, load_liked_set, load_submitter_names, normalize_keywords
from app.core.emoji_moderation import (
    EMOJI_STATUS_PENDING,
    apply_public_emoji_filter,
    is_public_emoji,
    reset_moderation_on_edit,
)
from app.core.ratelimit import comment_limiter, content_create_limiter, like_limiter, report_limiter
from app.db import get_session
from app.models import (
    CollectionEmoji,
    EmojiComment,
    EmojiLike,
    EmojiReport,
    EmojiSubmission,
    User,
)
from app.schemas import (
    Emoji,
    EmojiCommentCreate,
    EmojiCommentItem,
    EmojiCommentListResponse,
    EmojiCreate,
    EmojiListResponse,
    EmojiReportCreate,
    EmojiReportItem,
    EmojiUpdate,
)

router = APIRouter(prefix="/emojis", tags=["emojis"])

RANKING_WINDOWS = {
    "trending_day": timedelta(days=1),
    "trending_week": timedelta(days=7),
    "top_month": timedelta(days=30),
}


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _can_manage_submission(submission: EmojiSubmission, current_user: Optional[User]) -> bool:
    if current_user is None:
        return False
    if submission.submitter_id == current_user.id:
        return True
    return submission.submitter_id is None and submission.submitter_email == current_user.email


def _apply_list_filters(
    statement,
    *,
    search: Optional[str],
    category: Optional[str],
    favorites: bool,
    current_user: Optional[User],
):
    query = statement
    if favorites and current_user:
        liked_ids = select(EmojiLike.emoji_id).where(EmojiLike.user_id == current_user.id)
        query = query.where(col(EmojiSubmission.id).in_(liked_ids))

    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            or_(
                col(EmojiSubmission.title).ilike(search_term),
                col(EmojiSubmission.description).ilike(search_term),
                col(EmojiSubmission.keywords).ilike(search_term),
            )
        )

    if category:
        query = query.where(EmojiSubmission.category == category)

    return query


def _build_emoji_item(
    submission: EmojiSubmission,
    *,
    current_user: Optional[User],
    submitter_names: dict[int, str | None],
    like_counts: dict[int, int],
    comment_counts: dict[int, int],
    liked_set: set[int],
) -> Emoji:
    submission_id = submission.id or 0
    return Emoji(
        id=submission_id,
        symbol=submission.symbol,
        title=submission.title,
        description=submission.description,
        category=submission.category,
        keywords=submission.keyword_list,
        can_delete=_can_manage_submission(submission, current_user),
        like_count=like_counts.get(submission_id, 0),
        comment_count=comment_counts.get(submission_id, 0),
        is_liked=submission_id in liked_set,
        created_at=submission.created_at,
        submitter_id=submission.submitter_id,
        submitter_name=submitter_names.get(submission.submitter_id) if submission.submitter_id else None,
        moderation_status=submission.moderation_status,
        moderation_reason=submission.moderation_reason,
    )


def _build_ranking_query(
    *,
    sort: str,
    search: Optional[str],
    category: Optional[str],
    favorites: bool,
    current_user: Optional[User],
    offset: int,
    limit: int,
):
    lifetime_sq = (
        select(EmojiLike.emoji_id, func.count().label("cnt"))
        .group_by(EmojiLike.emoji_id)
        .subquery()
    )

    if sort in RANKING_WINDOWS:
        window_cutoff = datetime.now(timezone.utc) - RANKING_WINDOWS[sort]
        primary_sq = (
            select(EmojiLike.emoji_id, func.count().label("cnt"))
            .where(EmojiLike.created_at >= window_cutoff)
            .group_by(EmojiLike.emoji_id)
            .subquery()
        )
    else:
        primary_sq = lifetime_sq

    query = (
        select(EmojiSubmission, func.coalesce(lifetime_sq.c.cnt, 0))
        .outerjoin(lifetime_sq, EmojiSubmission.id == lifetime_sq.c.emoji_id)
    )
    if sort in RANKING_WINDOWS:
        query = query.outerjoin(primary_sq, EmojiSubmission.id == primary_sq.c.emoji_id)

    query = _apply_list_filters(
        apply_public_emoji_filter(query),
        search=search,
        category=category,
        favorites=favorites,
        current_user=current_user,
    )

    if sort in RANKING_WINDOWS:
        query = query.order_by(
            func.coalesce(primary_sq.c.cnt, 0).desc(),
            func.coalesce(lifetime_sq.c.cnt, 0).desc(),
            EmojiSubmission.created_at.desc(),
            EmojiSubmission.id.desc(),
        )
    else:
        query = query.order_by(
            func.coalesce(lifetime_sq.c.cnt, 0).desc(),
            EmojiSubmission.created_at.desc(),
            EmojiSubmission.id.desc(),
        )

    return query.offset(offset).limit(limit)


def _build_comment_item(
    comment: EmojiComment,
    *,
    author: User,
    current_user: Optional[User],
) -> EmojiCommentItem:
    return EmojiCommentItem(
        id=comment.id or 0,
        emoji_id=comment.emoji_id,
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        author_id=comment.author_id,
        author_name=author.display_name,
        author_avatar_url=author.avatar_url,
        can_delete=bool(
            current_user is not None
            and (current_user.id == comment.author_id or current_user.is_superuser)
        ),
    )


@router.get("", response_model=EmojiListResponse)
def list_emojis(
    search: Optional[str] = Query(None, description="Search by title, description, or keywords"),
    category: Optional[str] = Query(None, description="Filter by category"),
    sort: str = Query(
        "date_desc",
        description=(
            "Sort order: date_desc, date_asc, title_asc, title_desc, popular, "
            "trending_day, trending_week, top_month"
        ),
    ),
    limit: int = Query(50, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    favorites: bool = Query(False, description="Filter to only liked emojis (requires auth)"),
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
) -> EmojiListResponse:
    base_query = _apply_list_filters(
        apply_public_emoji_filter(select(EmojiSubmission)),
        search=search,
        category=category,
        favorites=favorites,
        current_user=current_user,
    )
    count_query = _apply_list_filters(
        apply_public_emoji_filter(select(func.count()).select_from(EmojiSubmission)),
        search=search,
        category=category,
        favorites=favorites,
        current_user=current_user,
    )
    total_submissions = session.exec(count_query).one()

    ranking_sort = sort == "popular" or sort in RANKING_WINDOWS
    if ranking_sort:
        ranking_rows = session.exec(
            _build_ranking_query(
                sort=sort,
                search=search,
                category=category,
                favorites=favorites,
                current_user=current_user,
                offset=offset,
                limit=limit,
            )
        ).all()
        submissions = [row[0] for row in ranking_rows]
        like_counts = {row[0].id: row[1] for row in ranking_rows if row[0].id is not None}
        emoji_ids = [s.id for s in submissions if s.id is not None]
    else:
        query = base_query
        if sort == "date_asc":
            query = query.order_by(EmojiSubmission.created_at.asc(), EmojiSubmission.id.asc())
        elif sort == "title_asc":
            query = query.order_by(EmojiSubmission.title.asc(), EmojiSubmission.id.asc())
        elif sort == "title_desc":
            query = query.order_by(EmojiSubmission.title.desc(), EmojiSubmission.id.desc())
        else:
            query = query.order_by(EmojiSubmission.created_at.desc(), EmojiSubmission.id.desc())
        submissions = session.exec(query.limit(limit).offset(offset)).all()
        emoji_ids = [submission.id for submission in submissions if submission.id is not None]
        like_counts = load_like_counts(session, emoji_ids)

    result_ids = [submission.id for submission in submissions if submission.id is not None]
    comment_counts = load_comment_counts(session, result_ids)
    liked_set = load_liked_set(session, current_user, result_ids)
    submitter_names = load_submitter_names(session, submissions)

    items = [
        _build_emoji_item(
            submission,
            current_user=current_user,
            submitter_names=submitter_names,
            like_counts=like_counts,
            comment_counts=comment_counts,
            liked_set=liked_set,
        )
        for submission in submissions
    ]

    return EmojiListResponse(items=items, total=total_submissions, limit=limit, offset=offset)


@router.post("", response_model=Emoji, status_code=status.HTTP_201_CREATED)
def create_emoji(
    payload: EmojiCreate,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Emoji:
    content_create_limiter.check(request)
    existing = session.exec(
        select(EmojiSubmission).where(
            EmojiSubmission.symbol == payload.symbol,
            EmojiSubmission.title == payload.title,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Emoji already exists")

    submission = EmojiSubmission(
        symbol=payload.symbol,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        submitter_email=current_user.email,
        submitter_id=current_user.id,
        moderation_status=EMOJI_STATUS_PENDING,
    )
    submission.keyword_list = normalize_keywords(payload.keywords)

    session.add(submission)
    try:
        session.commit()
    except IntegrityError as exc:
        # Concurrent insert raced past the existence check.
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Emoji already exists"
        ) from exc
    session.refresh(submission)

    return Emoji(
        id=submission.id or 0,
        symbol=submission.symbol,
        title=submission.title,
        description=submission.description,
        category=submission.category,
        keywords=submission.keyword_list,
        can_delete=True,
        moderation_status=submission.moderation_status,
    )


@router.put("/{emoji_id}", response_model=Emoji)
def update_emoji(
    emoji_id: int,
    payload: EmojiUpdate,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Emoji:
    content_create_limiter.check(request)
    submission = session.get(EmojiSubmission, emoji_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    if not _can_manage_submission(submission, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to edit")

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

    comment_counts = load_comment_counts(session, [emoji_id])
    return Emoji(
        id=submission.id or 0,
        symbol=submission.symbol,
        title=submission.title,
        description=submission.description,
        category=submission.category,
        keywords=submission.keyword_list,
        can_delete=True,
        comment_count=comment_counts.get(emoji_id, 0),
        moderation_status=submission.moderation_status,
        moderation_reason=submission.moderation_reason,
    )


@router.delete("/{emoji_id}", response_class=Response)
def delete_emoji(
    emoji_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    content_create_limiter.check(request)
    submission = session.get(EmojiSubmission, emoji_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    if not _can_manage_submission(submission, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete")

    session.exec(delete(CollectionEmoji).where(CollectionEmoji.emoji_id == emoji_id))
    session.exec(delete(EmojiLike).where(EmojiLike.emoji_id == emoji_id))
    session.exec(delete(EmojiComment).where(EmojiComment.emoji_id == emoji_id))
    session.exec(delete(EmojiReport).where(EmojiReport.emoji_id == emoji_id))

    session.delete(submission)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{emoji_id}/like", status_code=status.HTTP_201_CREATED)
def like_emoji(
    emoji_id: int,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    like_limiter.check(request)
    submission = session.get(EmojiSubmission, emoji_id)
    if not is_public_emoji(submission):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    existing = session.exec(
        select(EmojiLike).where(
            EmojiLike.user_id == current_user.id,
            EmojiLike.emoji_id == emoji_id,
        )
    ).first()
    if existing:
        response.status_code = status.HTTP_200_OK
        return {"detail": "already liked"}

    session.add(EmojiLike(user_id=current_user.id, emoji_id=emoji_id))
    try:
        session.commit()
    except IntegrityError:
        # Concurrent like raced past the existence check; the user's intent
        # (liked) is satisfied either way, so report idempotent success.
        session.rollback()
        response.status_code = status.HTTP_200_OK
        return {"detail": "already liked"}
    return {"detail": "liked"}


@router.delete("/{emoji_id}/like", response_class=Response)
def unlike_emoji(
    emoji_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    like_limiter.check(request)
    submission = session.get(EmojiSubmission, emoji_id)
    if not is_public_emoji(submission):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    existing = session.exec(
        select(EmojiLike).where(
            EmojiLike.user_id == current_user.id,
            EmojiLike.emoji_id == emoji_id,
        )
    ).first()
    if existing:
        session.delete(existing)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{emoji_id}/reports", response_model=EmojiReportItem)
def create_emoji_report(
    emoji_id: int,
    payload: EmojiReportCreate,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EmojiReportItem:
    report_limiter.check(request)
    submission = session.get(EmojiSubmission, emoji_id)
    if not is_public_emoji(submission):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    existing = session.exec(
        select(EmojiReport).where(
            EmojiReport.emoji_id == emoji_id,
            EmojiReport.reporter_id == current_user.id,
            EmojiReport.status == "open",
        )
    ).first()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return build_report_item(existing, emoji=submission, reporter=current_user, resolved_by=None)

    report = EmojiReport(
        emoji_id=emoji_id,
        reporter_id=current_user.id or 0,
        reason=payload.reason,
        details=_normalize_optional_text(payload.details),
        status="open",
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    response.status_code = status.HTTP_201_CREATED
    return build_report_item(report, emoji=submission, reporter=current_user, resolved_by=None)


@router.get("/{emoji_id}/comments", response_model=EmojiCommentListResponse)
def list_emoji_comments(
    emoji_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
) -> EmojiCommentListResponse:
    submission = session.get(EmojiSubmission, emoji_id)
    if not is_public_emoji(submission):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    base_query = select(EmojiComment).where(
        EmojiComment.emoji_id == emoji_id,
        EmojiComment.deleted_at.is_(None),
    )
    total = session.exec(
        select(func.count()).select_from(EmojiComment).where(
            EmojiComment.emoji_id == emoji_id,
            EmojiComment.deleted_at.is_(None),
        )
    ).one()
    comments = session.exec(
        base_query.order_by(EmojiComment.created_at.asc(), EmojiComment.id.asc()).offset(offset).limit(limit)
    ).all()

    author_ids = {comment.author_id for comment in comments}
    authors = {
        row[0]: row[1]
        for row in session.exec(select(User.id, User).where(User.id.in_(author_ids))).all()
    } if author_ids else {}

    items = [
        _build_comment_item(comment, author=authors[comment.author_id], current_user=current_user)
        for comment in comments
    ]
    return EmojiCommentListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/{emoji_id}/comments", response_model=EmojiCommentItem, status_code=status.HTTP_201_CREATED)
def create_emoji_comment(
    emoji_id: int,
    payload: EmojiCommentCreate,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EmojiCommentItem:
    comment_limiter.check(request)
    submission = session.get(EmojiSubmission, emoji_id)
    if not is_public_emoji(submission):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment cannot be blank")

    comment = EmojiComment(emoji_id=emoji_id, author_id=current_user.id or 0, body=body)
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return _build_comment_item(comment, author=current_user, current_user=current_user)


__all__ = ["router"]
