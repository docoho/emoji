from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_optional_user
from app.data.emojis import EMOJI_CATALOG
from app.db import get_session
from app.models import EmojiSubmission, User
from app.schemas import Emoji, EmojiCreate

SUBMISSION_ID_OFFSET = 1000

router = APIRouter(prefix="/emojis", tags=["emojis"])


@router.get("", response_model=list[Emoji])
def list_emojis(
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
) -> list[Emoji]:
    submissions = session.exec(select(EmojiSubmission)).all()
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
    return [*EMOJI_CATALOG, *merged]


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
