from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_optional_user
from app.core.emoji_moderation import apply_public_emoji_filter
from app.db import get_session
from app.models import Collection as CollectionModel, CollectionEmoji, EmojiComment, EmojiLike, EmojiSubmission, User
from app.schemas import (
    Collection,
    Emoji,
    UserMeUpdate,
    UserProfile,
    UserProfileAchievement,
    UserProfileHighlights,
    UserProfileStats,
    UserPublic,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=UserPublic)
def update_current_user(
    payload: UserMeUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> UserPublic:
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    if payload.bio is not None:
        current_user.bio = payload.bio
    current_user.touch()
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


def _build_collection_item(
    *,
    collection: CollectionModel,
    owner_name: Optional[str],
    emoji_count: int,
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
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        emojis=[],
    )


def _build_emoji_item(
    *,
    submission: EmojiSubmission,
    user_id: int,
    owner_name: Optional[str],
    current_user: Optional[User],
    like_counts: dict[int, int],
    comment_counts: dict[int, int],
    liked_set: set[int],
) -> Emoji:
    can_delete = bool(current_user is not None and submission.submitter_id == current_user.id)
    submission_id = submission.id or 0
    return Emoji(
        id=submission_id,
        symbol=submission.symbol,
        title=submission.title,
        description=submission.description,
        category=submission.category,
        keywords=submission.keyword_list,
        can_delete=can_delete,
        like_count=like_counts.get(submission_id, 0),
        comment_count=comment_counts.get(submission_id, 0),
        is_liked=submission_id in liked_set,
        submitter_id=user_id,
        submitter_name=owner_name,
        moderation_status=submission.moderation_status,
    )


def _build_achievements(
    *,
    emoji_count: int,
    total_likes_received: int,
    public_collection_count: int,
    categories_used_count: int,
) -> list[UserProfileAchievement]:
    definitions = [
        (
            "first_submission",
            "First Submission",
            "Share your first emoji with the community.",
            "spark",
            emoji_count,
            1,
        ),
        (
            "emoji_trio",
            "Emoji Trio",
            "Build a mini gallery with three submitted emojis.",
            "gallery",
            emoji_count,
            3,
        ),
        (
            "liked_creator",
            "Liked Creator",
            "Earn your first like across all submitted emojis.",
            "heart",
            total_likes_received,
            1,
        ),
        (
            "crowd_favorite",
            "Crowd Favorite",
            "Reach ten likes across your emoji catalog.",
            "trophy",
            total_likes_received,
            10,
        ),
        (
            "public_curator",
            "Public Curator",
            "Publish your first public collection.",
            "megaphone",
            public_collection_count,
            1,
        ),
        (
            "variety_pack",
            "Variety Pack",
            "Use three distinct categories across your submissions.",
            "palette",
            categories_used_count,
            3,
        ),
    ]

    achievements: list[UserProfileAchievement] = []
    for achievement_id, title, description, icon_key, current, target in definitions:
        achievements.append(
            UserProfileAchievement(
                id=achievement_id,
                title=title,
                description=description,
                icon_key=icon_key,
                earned=current >= target,
                progress_current=current,
                progress_target=target,
            )
        )
    return achievements


@router.get("/{user_id}", response_model=UserProfile)
def get_user_profile(
    user_id: int,
    emoji_limit: int = Query(50, ge=1, le=100),
    emoji_offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
) -> UserProfile:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_owner = current_user is not None and current_user.id == user_id

    # --- SQL aggregates for stats (no full table scan) ---
    emoji_count = int(session.exec(
        select(func.count()).select_from(EmojiSubmission).where(
            EmojiSubmission.moderation_status == "approved",
            EmojiSubmission.submitter_id == user_id,
        )
    ).one())

    like_sq = (
        select(EmojiLike.emoji_id, func.count().label("cnt"))
        .group_by(EmojiLike.emoji_id)
        .subquery()
    )
    total_likes = int(session.exec(
        select(func.coalesce(func.sum(like_sq.c.cnt), 0))
        .select_from(EmojiSubmission)
        .outerjoin(like_sq, EmojiSubmission.id == like_sq.c.emoji_id)
        .where(
            EmojiSubmission.moderation_status == "approved",
            EmojiSubmission.submitter_id == user_id,
        )
    ).one())

    cat_rows = session.exec(
        select(func.distinct(EmojiSubmission.category)).where(
            EmojiSubmission.moderation_status == "approved",
            EmojiSubmission.submitter_id == user_id,
            EmojiSubmission.category.is_not(None),
        )
    ).all()
    categories_used_count = len({c.strip() for c in cat_rows if c and c.strip()})

    # --- Top emoji via SQL ---
    top_submission = session.exec(
        select(EmojiSubmission)
        .outerjoin(like_sq, EmojiSubmission.id == like_sq.c.emoji_id)
        .where(
            EmojiSubmission.moderation_status == "approved",
            EmojiSubmission.submitter_id == user_id,
        )
        .order_by(
            func.coalesce(like_sq.c.cnt, 0).desc(),
            EmojiSubmission.created_at.desc(),
            EmojiSubmission.id.desc(),
        )
        .limit(1)
    ).first()

    # --- Capped emoji list ---
    submissions = session.exec(
        apply_public_emoji_filter(select(EmojiSubmission))
        .where(EmojiSubmission.submitter_id == user_id)
        .order_by(EmojiSubmission.created_at.desc())
        .limit(emoji_limit)
        .offset(emoji_offset)
    ).all()

    page_ids = [s.id for s in submissions if s.id is not None]
    top_id = top_submission.id if top_submission else None
    all_display_ids = list(set(page_ids) | ({top_id} if top_id is not None else set()))

    like_counts: dict[int, int] = {}
    comment_counts: dict[int, int] = {}
    if all_display_ids:
        count_rows = session.exec(
            select(EmojiLike.emoji_id, func.count().label("cnt"))
            .where(EmojiLike.emoji_id.in_(all_display_ids))
            .group_by(EmojiLike.emoji_id)
        ).all()
        like_counts = {row[0]: row[1] for row in count_rows}
        comment_rows = session.exec(
            select(EmojiComment.emoji_id, func.count().label("cnt"))
            .where(
                EmojiComment.emoji_id.in_(all_display_ids),
                EmojiComment.deleted_at.is_(None),
            )
            .group_by(EmojiComment.emoji_id)
        ).all()
        comment_counts = {row[0]: row[1] for row in comment_rows}

    liked_set: set[int] = set()
    if current_user and all_display_ids:
        liked_rows = session.exec(
            select(EmojiLike.emoji_id).where(
                EmojiLike.user_id == current_user.id,
                EmojiLike.emoji_id.in_(all_display_ids),
            )
        ).all()
        liked_set = set(liked_rows)

    # --- Collections ---
    all_collections = session.exec(
        select(CollectionModel)
        .where(CollectionModel.owner_id == user_id)
        .order_by(CollectionModel.created_at.desc())
    ).all()
    visible_collections = [
        collection for collection in all_collections if is_owner or collection.kind == "public"
    ]
    public_collections = [collection for collection in all_collections if collection.kind == "public"]

    collection_ids = [collection.id for collection in all_collections if collection.id is not None]
    collection_counts: dict[int, int] = {}
    if collection_ids:
        collection_count_rows = session.exec(
            select(CollectionEmoji.collection_id, func.count().label("cnt"))
            .where(CollectionEmoji.collection_id.in_(collection_ids))
            .group_by(CollectionEmoji.collection_id)
        ).all()
        collection_counts = {row[0]: row[1] for row in collection_count_rows}

    collection_items = [
        _build_collection_item(
            collection=collection,
            owner_name=user.display_name,
            emoji_count=collection_counts.get(collection.id or 0, 0),
        )
        for collection in visible_collections
    ]

    emojis = [
        _build_emoji_item(
            submission=submission,
            user_id=user_id,
            owner_name=user.display_name,
            current_user=current_user,
            like_counts=like_counts,
            comment_counts=comment_counts,
            liked_set=liked_set,
        )
        for submission in submissions
    ]

    top_emoji = None
    if top_submission is not None:
        top_emoji = _build_emoji_item(
            submission=top_submission,
            user_id=user_id,
            owner_name=user.display_name,
            current_user=current_user,
            like_counts=like_counts,
            comment_counts=comment_counts,
            liked_set=liked_set,
        )

    recent_public_collections = [
        _build_collection_item(
            collection=collection,
            owner_name=user.display_name,
            emoji_count=collection_counts.get(collection.id or 0, 0),
        )
        for collection in public_collections[:3]
    ]

    stats = UserProfileStats(
        emoji_count=emoji_count,
        total_likes_received=total_likes,
        collection_count=len(all_collections),
        public_collection_count=len(public_collections),
        categories_used_count=categories_used_count,
    )
    achievements = _build_achievements(
        emoji_count=stats.emoji_count,
        total_likes_received=stats.total_likes_received,
        public_collection_count=stats.public_collection_count,
        categories_used_count=stats.categories_used_count,
    )

    return UserProfile(
        id=user.id,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        created_at=user.created_at,
        emoji_count=emoji_count,
        total_likes_received=total_likes,
        collection_count=len(visible_collections),
        emojis=emojis,
        collections=collection_items,
        stats=stats,
        achievements=achievements,
        highlights=UserProfileHighlights(
            top_emoji=top_emoji,
            recent_public_collections=recent_public_collections,
        ),
    )


__all__ = ["router"]
