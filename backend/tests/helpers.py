from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from fastapi.testclient import TestClient

from app.db import get_session
from app.models import EmojiSubmission, User


@contextmanager
def test_session(client: TestClient) -> Generator:
    session_gen = client.app.dependency_overrides[get_session]()
    session = next(session_gen)
    try:
        yield session
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass


def set_user_superuser(client: TestClient, user_id: int) -> None:
    with test_session(client) as session:
        user = session.get(User, user_id)
        assert user is not None
        user.is_superuser = True
        session.add(user)
        session.commit()


def approve_emoji(
    client: TestClient,
    emoji_id: int,
    *,
    moderated_by_id: int | None = None,
) -> None:
    with test_session(client) as session:
        emoji = session.get(EmojiSubmission, emoji_id)
        assert emoji is not None
        emoji.moderation_status = "approved"
        emoji.moderation_reason = None
        emoji.moderated_at = datetime.now(timezone.utc)
        emoji.moderated_by_id = moderated_by_id
        session.add(emoji)
        session.commit()


def reject_emoji(
    client: TestClient,
    emoji_id: int,
    *,
    reason: str | None = None,
    moderated_by_id: int | None = None,
) -> None:
    with test_session(client) as session:
        emoji = session.get(EmojiSubmission, emoji_id)
        assert emoji is not None
        emoji.moderation_status = "rejected"
        emoji.moderation_reason = reason
        emoji.moderated_at = datetime.now(timezone.utc)
        emoji.moderated_by_id = moderated_by_id
        session.add(emoji)
        session.commit()
