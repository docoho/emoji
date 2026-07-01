from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.ratelimit import login_limiter, register_limiter
from tests.helpers import approve_emoji, set_user_superuser


def auth_headers(client: TestClient, email: str) -> tuple[dict[str, str], int]:
    register_limiter.reset()
    login_limiter.reset()
    register_response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "SecretPwd123!", "display_name": email.split("@")[0]},
    )
    login_response = client.post("/api/auth/login", json={"email": email, "password": "SecretPwd123!"})
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}, register_response.json()["id"]


def create_public_emoji(client: TestClient, headers: dict[str, str], *, symbol: str, title: str) -> int:
    response = client.post(
        "/api/emojis",
        json={"symbol": symbol, "title": title, "keywords": ["commentable"]},
        headers=headers,
    )
    emoji_id = response.json()["id"]
    approve_emoji(client, emoji_id)
    return emoji_id


def test_public_can_list_comments_for_approved_emoji(client: TestClient) -> None:
    creator_headers, _ = auth_headers(client, "comment-creator@example.com")
    commenter_headers, _ = auth_headers(client, "commenter@example.com")
    emoji_id = create_public_emoji(client, creator_headers, symbol="💬", title="Chat Bubble")

    created = client.post(
        f"/api/emojis/{emoji_id}/comments",
        json={"body": "Love this one"},
        headers=commenter_headers,
    )
    assert created.status_code == 201

    listing = client.get(f"/api/emojis/{emoji_id}/comments")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["items"][0]["body"] == "Love this one"


def test_comment_creation_requires_authentication(client: TestClient) -> None:
    creator_headers, _ = auth_headers(client, "auth-comment-creator@example.com")
    emoji_id = create_public_emoji(client, creator_headers, symbol="🔒", title="Locked Comments")

    response = client.post(f"/api/emojis/{emoji_id}/comments", json={"body": "No auth"})
    assert response.status_code == 401


def test_blank_comments_are_rejected(client: TestClient) -> None:
    creator_headers, _ = auth_headers(client, "blank-comment-creator@example.com")
    commenter_headers, _ = auth_headers(client, "blank-commenter@example.com")
    emoji_id = create_public_emoji(client, creator_headers, symbol="🫥", title="Blank Check")

    response = client.post(
        f"/api/emojis/{emoji_id}/comments",
        json={"body": "   "},
        headers=commenter_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Comment cannot be blank"


def test_comment_delete_permissions_and_soft_delete_counts(client: TestClient) -> None:
    creator_headers, _ = auth_headers(client, "delete-comment-creator@example.com")
    author_headers, _ = auth_headers(client, "delete-comment-author@example.com")
    other_headers, _ = auth_headers(client, "delete-comment-other@example.com")
    admin_headers, admin_id = auth_headers(client, "delete-comment-admin@example.com")
    set_user_superuser(client, admin_id)

    emoji_id = create_public_emoji(client, creator_headers, symbol="🧵", title="Threadless")
    created = client.post(
        f"/api/emojis/{emoji_id}/comments",
        json={"body": "Keep me for a moment"},
        headers=author_headers,
    )
    comment_id = created.json()["id"]

    forbidden = client.delete(f"/api/comments/{comment_id}", headers=other_headers)
    assert forbidden.status_code == 403

    deleted = client.delete(f"/api/comments/{comment_id}", headers=admin_headers)
    assert deleted.status_code == 204

    listing = client.get(f"/api/emojis/{emoji_id}/comments")
    assert listing.json()["total"] == 0

    emoji_list = client.get("/api/emojis")
    item = next(item for item in emoji_list.json()["items"] if item["id"] == emoji_id)
    assert item["comment_count"] == 0


def test_comment_count_appears_in_emoji_list(client: TestClient) -> None:
    creator_headers, _ = auth_headers(client, "count-creator@example.com")
    commenter_headers, _ = auth_headers(client, "count-commenter@example.com")
    emoji_id = create_public_emoji(client, creator_headers, symbol="🧮", title="Counted")

    client.post(
        f"/api/emojis/{emoji_id}/comments",
        json={"body": "First"},
        headers=commenter_headers,
    )
    client.post(
        f"/api/emojis/{emoji_id}/comments",
        json={"body": "Second"},
        headers=creator_headers,
    )

    listing = client.get("/api/emojis")
    item = next(item for item in listing.json()["items"] if item["id"] == emoji_id)
    assert item["comment_count"] == 2


def test_comments_are_blocked_for_non_public_emojis(client: TestClient) -> None:
    creator_headers, _ = auth_headers(client, "private-comment-creator@example.com")
    commenter_headers, _ = auth_headers(client, "private-commenter@example.com")
    response = client.post(
        "/api/emojis",
        json={"symbol": "⏳", "title": "Pending Comment", "keywords": ["pending"]},
        headers=creator_headers,
    )
    emoji_id = response.json()["id"]

    listing = client.get(f"/api/emojis/{emoji_id}/comments")
    posting = client.post(
        f"/api/emojis/{emoji_id}/comments",
        json={"body": "Should not work"},
        headers=commenter_headers,
    )
    assert listing.status_code == 404
    assert posting.status_code == 404
