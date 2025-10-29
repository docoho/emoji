from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, col, or_, select

from app.api.deps import get_current_user, get_optional_user
from app.data.emojis import EMOJI_CATALOG
from app.db import get_session
from app.models import EmojiSubmission, User
from app.schemas import Emoji, EmojiCreate, EmojiListResponse, EmojiUpdate

SUBMISSION_ID_OFFSET = 1000

router = APIRouter(prefix="/emojis", tags=["emojis"])


@router.get("", response_model=EmojiListResponse)
def list_emojis(
    search: Optional[str] = Query(None, description="Search by title, description, or keywords"),
    category: Optional[str] = Query(None, description="Filter by category"),
    sort: str = Query("date_desc", description="Sort order: date_desc, date_asc, title_asc, title_desc"),
    limit: int = Query(50, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
) -> EmojiListResponse:
    query = select(EmojiSubmission)
    
    # Apply search filter
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            or_(
                col(EmojiSubmission.title).ilike(search_term),
                col(EmojiSubmission.description).ilike(search_term),
                col(EmojiSubmission.keywords).ilike(search_term),
            )
        )
    
    # Apply category filter
    if category:
        query = query.where(EmojiSubmission.category == category)
    
    # Apply sorting
    if sort == "date_asc":
        query = query.order_by(EmojiSubmission.created_at.asc())
    elif sort == "title_asc":
        query = query.order_by(EmojiSubmission.title.asc())
    elif sort == "title_desc":
        query = query.order_by(EmojiSubmission.title.desc())
    else:  # date_desc (default)
        query = query.order_by(EmojiSubmission.created_at.desc())
    
    # Get total count before pagination
    count_query = select(EmojiSubmission)
    if search:
        search_term = f"%{search.lower()}%"
        count_query = count_query.where(
            or_(
                col(EmojiSubmission.title).ilike(search_term),
                col(EmojiSubmission.description).ilike(search_term),
                col(EmojiSubmission.keywords).ilike(search_term),
            )
        )
    if category:
        count_query = count_query.where(EmojiSubmission.category == category)
    
    total_submissions = len(session.exec(count_query).all())
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    submissions = session.exec(query).all()
    
    # Convert to response format
    merged: list[Emoji] = []
    for submission in submissions:
        can_delete = False
        if current_user is not None:
            if submission.submitter_id == current_user.id:
                can_delete = True
            elif submission.submitter_id is None and submission.submitter_email == current_user.email:
                can_delete = True
        merged.append(
            Emoji(
                id=SUBMISSION_ID_OFFSET + submission.id,
                symbol=submission.symbol,
                title=submission.title,
                description=submission.description,
                category=submission.category,
                keywords=submission.keyword_list,
                submitter_email=submission.submitter_email,
                can_delete=can_delete,
            )
        )
    
    # Include catalog emojis only on first page with no filters
    if offset == 0 and not search and not category:
        catalog_emojis = EMOJI_CATALOG[:limit]
        remaining_slots = limit - len(catalog_emojis)
        if remaining_slots > 0:
            all_items = [*catalog_emojis, *merged[:remaining_slots]]
        else:
            all_items = catalog_emojis
        total = len(EMOJI_CATALOG) + total_submissions
    else:
        all_items = merged
        total = total_submissions
    
    return EmojiListResponse(
        items=all_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=Emoji, status_code=status.HTTP_201_CREATED)
def create_emoji(
    payload: EmojiCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Emoji:
    normalized_keywords = sorted({tag.strip() for tag in payload.keywords if tag.strip()})
    for emoji in EMOJI_CATALOG:
        if emoji.symbol == payload.symbol and emoji.title.lower() == payload.title.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Emoji already exists")

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
        submitter_email=payload.submitter_email or current_user.email,
        submitter_id=current_user.id,
    )
    submission.keyword_list = normalized_keywords

    session.add(submission)
    session.commit()
    session.refresh(submission)

    return Emoji(
        id=SUBMISSION_ID_OFFSET + submission.id,
        symbol=submission.symbol,
        title=submission.title,
        description=submission.description,
        category=submission.category,
        keywords=submission.keyword_list,
        submitter_email=submission.submitter_email,
        can_delete=True,
    )


@router.put("/{emoji_id}", response_model=Emoji)
def update_emoji(
    emoji_id: int,
    payload: EmojiUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Emoji:
    if emoji_id < SUBMISSION_ID_OFFSET:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    submission_id = emoji_id - SUBMISSION_ID_OFFSET
    submission = session.get(EmojiSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    if submission.submitter_id == current_user.id:
        pass
    elif submission.submitter_id is None and submission.submitter_email == current_user.email:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to edit")

    if payload.symbol is not None:
        submission.symbol = payload.symbol
    if payload.title is not None:
        submission.title = payload.title
    if payload.description is not None:
        submission.description = payload.description
    if payload.category is not None:
        submission.category = payload.category
    if payload.keywords is not None:
        submission.keyword_list = payload.keywords

    session.add(submission)
    session.commit()
    session.refresh(submission)

    return Emoji(
        id=SUBMISSION_ID_OFFSET + submission.id,
        symbol=submission.symbol,
        title=submission.title,
        description=submission.description,
        category=submission.category,
        keywords=submission.keyword_list,
        submitter_email=submission.submitter_email,
        can_delete=True,
    )


@router.delete("/{emoji_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_emoji(
    emoji_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    if emoji_id < SUBMISSION_ID_OFFSET:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    submission_id = emoji_id - SUBMISSION_ID_OFFSET
    submission = session.get(EmojiSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emoji not found")

    if submission.submitter_id == current_user.id:
        pass
    elif submission.submitter_id is None and submission.submitter_email == current_user.email:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete")

    session.delete(submission)
    session.commit()


__all__ = ["router"]
