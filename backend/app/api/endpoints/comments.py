from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db import get_session
from app.models import EmojiComment, User

router = APIRouter(prefix="/comments", tags=["comments"])


@router.delete("/{comment_id}", response_class=Response)
def delete_comment(
    comment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    comment = session.get(EmojiComment, comment_id)
    if comment is None or comment.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if current_user.id != comment.author_id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete comment")

    comment.deleted_at = datetime.now(timezone.utc)
    comment.updated_at = comment.deleted_at
    session.add(comment)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
