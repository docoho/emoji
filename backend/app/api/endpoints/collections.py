from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, or_, select

from app.api.deps import get_current_user, get_optional_user
from app.core.emoji_moderation import EMOJI_STATUS_APPROVED, apply_public_emoji_filter, is_public_emoji
from app.core.ratelimit import content_create_limiter
from app.db import get_session
from app.models import (
    Collection as CollectionModel,
    CollectionEmoji,
    EmojiComment,
    EmojiLike,
    EmojiSubmission,
    User,
)
from app.schemas import (
    Collection,
    CollectionCreate,
    CollectionEmojiAddRequest,
    CollectionListResponse,
    CollectionUpdate,
    Emoji,
    EmojiCollectionsResponse,
    EmojiCollectionsUpdate,
)

router = APIRouter(tags=["collections"])


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "collection"


def _unique_slug(session: Session, owner_id: int, candidate: str) -> str:
    slug = _slugify(candidate)
    base_slug = slug
    suffix = 2
    while session.exec(
        select(CollectionModel.id).where(
            CollectionModel.owner_id == owner_id,
            CollectionModel.slug == slug,
        )
    ).first():
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def _collection_response(
    collection: CollectionModel,
    *,
    emoji_count: int = 0,
    contains_emoji: bool = False,
    owner_name: Optional[str] = None,
    emojis: Optional[list[Emoji]] = None,
) -> Collection:
    return Collection(
        id=collection.id,
        slug=collection.slug,
        name=collection.name,
        description=collection.description,
        kind=collection.kind,  # type: ignore[arg-type]
        owner_id=collection.owner_id,
        owner_name=owner_name,
        emoji_count=emoji_count,
        contains_emoji=contains_emoji,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        emojis=emojis or [],
    )


def _load_owner_names(session: Session, owner_ids: set[int]) -> dict[int, str | None]:
    if not owner_ids:
        return {}
    rows = session.exec(select(User.id, User.display_name).where(User.id.in_(owner_ids))).all()
    return {row[0]: row[1] for row in rows}


def _load_collection_counts(session: Session, collection_ids: list[int]) -> dict[int, int]:
    if not collection_ids:
        return {}
    rows = session.exec(
        select(CollectionEmoji.collection_id, func.count().label("cnt"))
        .join(EmojiSubmission, EmojiSubmission.id == CollectionEmoji.emoji_id)
        .where(CollectionEmoji.collection_id.in_(collection_ids))
        .where(EmojiSubmission.moderation_status == EMOJI_STATUS_APPROVED)
        .group_by(CollectionEmoji.collection_id)
    ).all()
    return {row[0]: row[1] for row in rows}


def _count_collection_emojis(session: Session, collection_id: int) -> int:
    return int(
        session.exec(
            select(func.count())
            .select_from(CollectionEmoji)
            .join(EmojiSubmission, EmojiSubmission.id == CollectionEmoji.emoji_id)
            .where(
                CollectionEmoji.collection_id == collection_id,
                EmojiSubmission.moderation_status == EMOJI_STATUS_APPROVED,
            )
        ).one()
    )


def _load_collection_emojis(
    session: Session,
    collection_id: int,
    *,
    search: Optional[str] = None,
    category: Optional[str] = None,
    sort: str = "added_desc",
    limit: Optional[int] = None,
    offset: int = 0,
    current_user: Optional[User],
) -> list[Emoji]:
    query = (
        apply_public_emoji_filter(select(EmojiSubmission))
        .join(CollectionEmoji, CollectionEmoji.emoji_id == EmojiSubmission.id)
        .where(CollectionEmoji.collection_id == collection_id)
    )

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

    if sort == "added_asc":
        query = query.order_by(CollectionEmoji.created_at.asc())
    elif sort == "title_asc":
        query = query.order_by(EmojiSubmission.title.asc())
    elif sort == "title_desc":
        query = query.order_by(EmojiSubmission.title.desc())
    else:
        query = query.order_by(CollectionEmoji.created_at.desc())

    if limit is not None:
        query = query.offset(offset).limit(limit)

    submissions = session.exec(query).all()

    emoji_ids = [submission.id for submission in submissions]
    like_counts: dict[int, int] = {}
    comment_counts: dict[int, int] = {}
    if emoji_ids:
        like_rows = session.exec(
            select(EmojiLike.emoji_id, func.count().label("cnt"))
            .where(EmojiLike.emoji_id.in_(emoji_ids))
            .group_by(EmojiLike.emoji_id)
        ).all()
        like_counts = {row[0]: row[1] for row in like_rows}
        comment_rows = session.exec(
            select(EmojiComment.emoji_id, func.count().label("cnt"))
            .where(
                EmojiComment.emoji_id.in_(emoji_ids),
                EmojiComment.deleted_at.is_(None),
            )
            .group_by(EmojiComment.emoji_id)
        ).all()
        comment_counts = {row[0]: row[1] for row in comment_rows}

    liked_set: set[int] = set()
    if current_user is not None and emoji_ids:
        liked_rows = session.exec(
            select(EmojiLike.emoji_id).where(
                EmojiLike.user_id == current_user.id,
                EmojiLike.emoji_id.in_(emoji_ids),
            )
        ).all()
        liked_set = set(liked_rows)

    submitter_ids = {submission.submitter_id for submission in submissions if submission.submitter_id}
    submitter_names: dict[int, str | None] = {}
    if submitter_ids:
        user_rows = session.exec(
            select(User.id, User.display_name).where(User.id.in_(submitter_ids))
        ).all()
        submitter_names = {row[0]: row[1] for row in user_rows}

    emojis: list[Emoji] = []
    for submission in submissions:
        can_delete = False
        if current_user is not None:
            if submission.submitter_id == current_user.id:
                can_delete = True
            elif submission.submitter_id is None and submission.submitter_email == current_user.email:
                can_delete = True
        emojis.append(
            Emoji(
                id=submission.id,
                symbol=submission.symbol,
                title=submission.title,
                description=submission.description,
                category=submission.category,
                keywords=submission.keyword_list,
                can_delete=can_delete,
                like_count=like_counts.get(submission.id, 0),
                comment_count=comment_counts.get(submission.id, 0),
                is_liked=submission.id in liked_set,
                submitter_id=submission.submitter_id,
                submitter_name=submitter_names.get(submission.submitter_id)
                if submission.submitter_id
                else None,
                moderation_status=submission.moderation_status,
            )
        )

    return emojis


def _get_collection_or_404(session: Session, collection_id: int) -> CollectionModel:
    collection = session.get(CollectionModel, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return collection


def _require_owner(collection: CollectionModel, current_user: User) -> None:
    if collection.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to edit")


def _approved_emoji_count_subquery():
    return (
        select(CollectionEmoji.collection_id, func.count().label("cnt"))
        .join(EmojiSubmission, EmojiSubmission.id == CollectionEmoji.emoji_id)
        .where(EmojiSubmission.moderation_status == EMOJI_STATUS_APPROVED)
        .group_by(CollectionEmoji.collection_id)
        .subquery()
    )


@router.get("/collections", response_model=CollectionListResponse)
def list_collections(
    owner_id: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort: str = Query(default="updated_desc"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
) -> CollectionListResponse:
    viewer_id = current_user.id if current_user else None
    # Personal collections are visible only to their owner. Build the predicate
    # explicitly per branch: `Column == None` emits `IS NULL` in SQLAlchemy, so
    # a single `or_(kind != "personal", owner_id == viewer_id)` would, for an
    # anonymous viewer, match every NULL-owner row and leak data.
    if viewer_id is None:
        visibility = CollectionModel.kind != "personal"
    else:
        visibility = or_(
            CollectionModel.kind != "personal",
            CollectionModel.owner_id == viewer_id,
        )
    search_filter = None
    if search:
        search_term = f"%{search.lower()}%"
        search_filter = or_(
            col(CollectionModel.name).ilike(search_term),
            col(CollectionModel.description).ilike(search_term),
            col(CollectionModel.slug).ilike(search_term),
        )

    count_query = select(func.count()).select_from(CollectionModel)
    if visibility is not None:
        count_query = count_query.where(visibility)
    if owner_id is not None:
        count_query = count_query.where(CollectionModel.owner_id == owner_id)
    if search_filter is not None:
        count_query = count_query.where(search_filter)
    total = int(session.exec(count_query).one())

    if sort == "emoji_count_desc":
        count_sq = _approved_emoji_count_subquery()
        query = (
            select(CollectionModel)
            .outerjoin(count_sq, CollectionModel.id == count_sq.c.collection_id)
        )
        if visibility is not None:
            query = query.where(visibility)
        if owner_id is not None:
            query = query.where(CollectionModel.owner_id == owner_id)
        if search_filter is not None:
            query = query.where(search_filter)
        query = query.order_by(
            func.coalesce(count_sq.c.cnt, 0).desc(),
            CollectionModel.updated_at.desc(),
            CollectionModel.id.desc(),
        )
    else:
        query = select(CollectionModel)
        if visibility is not None:
            query = query.where(visibility)
        if owner_id is not None:
            query = query.where(CollectionModel.owner_id == owner_id)
        if search_filter is not None:
            query = query.where(search_filter)
        if sort == "created_desc":
            query = query.order_by(
                CollectionModel.created_at.desc(),
                CollectionModel.id.desc(),
            )
        elif sort == "name_asc":
            query = query.order_by(
                func.lower(CollectionModel.name).asc(),
                CollectionModel.id.asc(),
            )
        else:
            query = query.order_by(
                CollectionModel.updated_at.desc(),
                CollectionModel.id.desc(),
            )

    collections = session.exec(query.offset(offset).limit(limit)).all()

    collection_ids = [c.id for c in collections if c.id is not None]
    emoji_counts = _load_collection_counts(session, collection_ids)
    owner_names = _load_owner_names(session, {c.owner_id for c in collections})

    items = [
        _collection_response(
            collection,
            emoji_count=emoji_counts.get(collection.id, 0),
            owner_name=owner_names.get(collection.owner_id),
        )
        for collection in collections
    ]
    return CollectionListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/collections", response_model=Collection, status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionCreate,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Collection:
    content_create_limiter.check(request)
    slug_source = payload.slug or payload.name
    collection = CollectionModel(
        owner_id=current_user.id,
        slug=_unique_slug(session, current_user.id, slug_source),
        name=payload.name,
        description=payload.description,
        kind=payload.kind,
    )
    session.add(collection)
    session.commit()
    session.refresh(collection)
    return _collection_response(collection, owner_name=current_user.display_name)


@router.get("/collections/{collection_id}", response_model=Collection)
def get_collection(
    collection_id: int,
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    sort: str = Query(default="added_desc"),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
) -> Collection:
    collection = _get_collection_or_404(session, collection_id)

    if collection.kind == "personal" and (
        current_user is None or current_user.id != collection.owner_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    emojis = _load_collection_emojis(
        session,
        collection_id,
        search=search,
        category=category,
        sort=sort,
        limit=limit,
        offset=offset,
        current_user=current_user,
    )
    owner = session.get(User, collection.owner_id)
    return _collection_response(
        collection,
        emoji_count=_count_collection_emojis(session, collection_id),
        owner_name=owner.display_name if owner else None,
        emojis=emojis,
    )


@router.put("/collections/{collection_id}", response_model=Collection)
def update_collection(
    collection_id: int,
    payload: CollectionUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Collection:
    collection = _get_collection_or_404(session, collection_id)
    _require_owner(collection, current_user)

    if payload.name is not None:
        collection.name = payload.name
    if payload.description is not None:
        collection.description = payload.description
    if payload.kind is not None:
        collection.kind = payload.kind

    collection.touch()
    session.add(collection)
    session.commit()
    session.refresh(collection)
    return _collection_response(collection, owner_name=current_user.display_name)


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    collection = _get_collection_or_404(session, collection_id)
    _require_owner(collection, current_user)

    memberships = session.exec(
        select(CollectionEmoji).where(CollectionEmoji.collection_id == collection_id)
    ).all()
    for membership in memberships:
        session.delete(membership)
    session.delete(collection)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

def _add_emoji_to_collection(
    collection_id: int,
    emoji_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    content_create_limiter.check(request)
    collection = _get_collection_or_404(session, collection_id)
    _require_owner(collection, current_user)

    submission = session.get(EmojiSubmission, emoji_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")
    if not is_public_emoji(submission):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved emojis can be added to collections",
        )

    existing = session.exec(
        select(CollectionEmoji).where(
            CollectionEmoji.collection_id == collection_id,
            CollectionEmoji.emoji_id == emoji_id,
        )
    ).first()
    if existing:
        return Response(
            status_code=status.HTTP_200_OK,
            content='{"detail":"already added"}',
            media_type="application/json",
        )

    session.add(CollectionEmoji(collection_id=collection_id, emoji_id=emoji_id))
    collection.touch()
    session.add(collection)
    try:
        session.commit()
    except IntegrityError:
        # Concurrent add raced past the existence check; the membership exists,
        # so report idempotent success.
        session.rollback()
        return Response(
            status_code=status.HTTP_200_OK,
            content='{"detail":"already added"}',
            media_type="application/json",
        )
    return Response(
        status_code=status.HTTP_201_CREATED,
        content='{"detail":"added"}',
        media_type="application/json",
    )

@router.post("/collections/{collection_id}/emojis", status_code=status.HTTP_201_CREATED)
def add_emoji_to_collection(
    collection_id: int,
    payload: CollectionEmojiAddRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    return _add_emoji_to_collection(collection_id, payload.emoji_id, request, session, current_user)


@router.post("/emojis/{emoji_id}/collections/{collection_id}", status_code=status.HTTP_201_CREATED)
def add_emoji_to_collection_legacy(
    emoji_id: int,
    collection_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    return _add_emoji_to_collection(collection_id, emoji_id, request, session, current_user)


@router.delete("/collections/{collection_id}/emojis/{emoji_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_emoji_from_collection(
    collection_id: int,
    emoji_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    collection = _get_collection_or_404(session, collection_id)
    _require_owner(collection, current_user)

    existing = session.exec(
        select(CollectionEmoji).where(
            CollectionEmoji.collection_id == collection_id,
            CollectionEmoji.emoji_id == emoji_id,
        )
    ).first()
    if existing:
        session.delete(existing)
        collection.touch()
        session.add(collection)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/emojis/{emoji_id}/collections", response_model=EmojiCollectionsResponse)
def get_emoji_collections(
    emoji_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EmojiCollectionsResponse:
    submission = session.get(EmojiSubmission, emoji_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")
    if not is_public_emoji(submission):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved emojis can be added to collections",
        )

    collections = session.exec(
        select(CollectionModel)
        .where(CollectionModel.owner_id == current_user.id)
        .order_by(CollectionModel.created_at.desc())
    ).all()

    selected_rows = session.exec(
        select(CollectionEmoji.collection_id).where(
            CollectionEmoji.emoji_id == emoji_id,
            CollectionEmoji.collection_id.in_([collection.id for collection in collections if collection.id is not None]),
        )
    ).all()
    selected_ids = list(selected_rows)

    collection_ids = [collection.id for collection in collections if collection.id is not None]
    emoji_counts = _load_collection_counts(session, collection_ids)
    owner_names = _load_owner_names(session, {collection.owner_id for collection in collections})

    items = [
        _collection_response(
            collection,
            emoji_count=emoji_counts.get(collection.id, 0),
            contains_emoji=collection.id in selected_ids,
            owner_name=owner_names.get(collection.owner_id),
        )
        for collection in collections
    ]
    return EmojiCollectionsResponse(
        emoji_id=emoji_id,
        selected_collection_ids=selected_ids,
        collections=items,
    )


@router.put("/emojis/{emoji_id}/collections", response_model=EmojiCollectionsResponse)
def update_emoji_collections(
    emoji_id: int,
    payload: EmojiCollectionsUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EmojiCollectionsResponse:
    submission = session.get(EmojiSubmission, emoji_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")
    if not is_public_emoji(submission):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved emojis can be added to collections",
        )

    requested_ids: list[int] = []
    for collection_id in payload.collection_ids:
        if collection_id not in requested_ids:
            requested_ids.append(collection_id)

    requested_collections = []
    if requested_ids:
        requested_collections = session.exec(
            select(CollectionModel).where(CollectionModel.id.in_(requested_ids))
        ).all()
        if len(requested_collections) != len(requested_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    for collection in requested_collections:
        if collection.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to edit")

    target_ids = set(requested_ids)

    current_rows = session.exec(
        select(CollectionEmoji.collection_id).join(
            CollectionModel, CollectionModel.id == CollectionEmoji.collection_id
        ).where(
            CollectionEmoji.emoji_id == emoji_id,
            CollectionModel.owner_id == current_user.id,
        )
    ).all()
    current_owned_ids = set(current_rows)

    to_remove = current_owned_ids - target_ids
    to_add = target_ids - current_owned_ids

    if to_remove:
        remove_rows = session.exec(
            select(CollectionEmoji).where(
                CollectionEmoji.emoji_id == emoji_id,
                CollectionEmoji.collection_id.in_(to_remove),
            )
        ).all()
        for row in remove_rows:
            session.delete(row)

    if to_add:
        session.add_all(
            [CollectionEmoji(collection_id=collection_id, emoji_id=emoji_id) for collection_id in to_add]
        )

    affected_ids = to_remove | to_add
    if affected_ids:
        affected_collections = session.exec(
            select(CollectionModel).where(CollectionModel.id.in_(affected_ids))
        ).all()
        for collection in affected_collections:
            collection.touch()
            session.add(collection)

    session.commit()
    return get_emoji_collections(emoji_id=emoji_id, session=session, current_user=current_user)


__all__ = ["router"]
