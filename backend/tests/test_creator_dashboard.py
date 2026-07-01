from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import select

from app.core.ratelimit import login_limiter, register_limiter
from app.models import CollectionEmoji, User
from tests.helpers import approve_emoji, reject_emoji, test_session as db_session


def register_and_login(
    client: TestClient,
    email: str,
    *,
    display_name: str = "Creator",
) -> tuple[dict[str, str], int]:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "SecretPwd123!",
            "display_name": display_name,
        },
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "SecretPwd123!"},
    )
    assert login_response.status_code == 200
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}, user_id


def create_creator_emoji(
    client: TestClient,
    headers: dict[str, str],
    *,
    symbol: str,
    title: str,
    intent: str = "submit",
    keywords: list[str] | None = None,
    description: str | None = None,
    category: str | None = None,
) -> dict:
    response = client.post(
        "/api/creator/emojis",
        json={
            "symbol": symbol,
            "title": title,
            "description": description,
            "category": category,
            "keywords": keywords or ["test"],
            "intent": intent,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def create_collection(client: TestClient, headers: dict[str, str], *, name: str) -> dict:
    response = client.post(
        "/api/collections",
        json={"name": name, "kind": "personal"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def like_emoji_many_times(client: TestClient, emoji_id: int, count: int) -> None:
    for index in range(count):
        register_limiter.reset()
        login_limiter.reset()
        headers, _ = register_and_login(client, f"fan{emoji_id}-{index}@example.com", display_name="Fan")
        response = client.post(f"/api/emojis/{emoji_id}/like", headers=headers)
        assert response.status_code == 201


def test_creator_draft_stays_private_until_submitted(client: TestClient) -> None:
    headers, _ = register_and_login(client, "drafts@example.com")
    draft = create_creator_emoji(
        client,
        headers,
        symbol="🧰",
        title="Toolbox Draft",
        intent="draft",
        keywords=["tools", "draft"],
    )

    assert draft["moderation_status"] == "draft"

    creator_list = client.get("/api/creator/emojis?status=draft", headers=headers)
    assert creator_list.status_code == 200
    assert [item["id"] for item in creator_list.json()["items"]] == [draft["id"]]

    public_list = client.get("/api/emojis", headers=headers)
    assert public_list.status_code == 200
    assert all(item["id"] != draft["id"] for item in public_list.json()["items"])

    submit_response = client.post(f"/api/creator/emojis/{draft['id']}/submit", headers=headers)
    assert submit_response.status_code == 200
    assert submit_response.json()["moderation_status"] == "pending"


def test_rejected_creator_emoji_can_be_edited_and_resubmitted(client: TestClient) -> None:
    headers, _ = register_and_login(client, "rejected@example.com")
    emoji = create_creator_emoji(
        client,
        headers,
        symbol="🚧",
        title="Blocked",
        intent="submit",
        keywords=["road"],
    )
    reject_emoji(client, emoji["id"], reason="Needs better description")

    update_response = client.put(
        f"/api/creator/emojis/{emoji['id']}",
        json={"description": "Updated before resubmitting"},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["moderation_status"] == "rejected"
    assert update_response.json()["moderation_reason"] == "Needs better description"

    submit_response = client.post(f"/api/creator/emojis/{emoji['id']}/submit", headers=headers)
    assert submit_response.status_code == 200
    body = submit_response.json()
    assert body["moderation_status"] == "pending"
    assert body["moderation_reason"] is None


def test_creator_list_filters_owner_emojis_by_status(client: TestClient) -> None:
    owner_headers, _ = register_and_login(client, "owner-status@example.com")
    other_headers, _ = register_and_login(client, "other-status@example.com")

    draft = create_creator_emoji(client, owner_headers, symbol="📝", title="Draft One", intent="draft")
    pending = create_creator_emoji(client, owner_headers, symbol="📮", title="Pending One", intent="submit")
    rejected = create_creator_emoji(client, owner_headers, symbol="🪫", title="Rejected One", intent="submit")
    approved = create_creator_emoji(client, owner_headers, symbol="🌟", title="Approved One", intent="submit")
    create_creator_emoji(client, other_headers, symbol="🙅", title="Other Owner", intent="draft")

    reject_emoji(client, rejected["id"], reason="Not ready")
    approve_emoji(client, approved["id"])

    draft_items = client.get("/api/creator/emojis?status=draft", headers=owner_headers).json()["items"]
    assert [item["id"] for item in draft_items] == [draft["id"]]

    pending_items = client.get("/api/creator/emojis?status=pending", headers=owner_headers).json()["items"]
    assert [item["id"] for item in pending_items] == [pending["id"]]

    rejected_items = client.get("/api/creator/emojis?status=rejected", headers=owner_headers).json()["items"]
    assert [item["id"] for item in rejected_items] == [rejected["id"]]

    approved_items = client.get("/api/creator/emojis?status=approved", headers=owner_headers).json()["items"]
    assert [item["id"] for item in approved_items] == [approved["id"]]


def test_duplicate_endpoint_creates_unique_draft_without_collection_membership(client: TestClient) -> None:
    headers, _ = register_and_login(client, "duplicate@example.com")
    original = create_creator_emoji(
        client,
        headers,
        symbol="🛰️",
        title="Satellite",
        intent="submit",
        keywords=["space", "orbit"],
        description="Original launch",
        category="Objects",
    )
    approve_emoji(client, original["id"])

    collection = create_collection(client, headers, name="Space Shelf")
    add_response = client.post(
        f"/api/collections/{collection['id']}/emojis",
        json={"emoji_id": original["id"]},
        headers=headers,
    )
    assert add_response.status_code == 201

    first_copy_response = client.post(f"/api/creator/emojis/{original['id']}/duplicate", headers=headers)
    assert first_copy_response.status_code == 201
    first_copy = first_copy_response.json()
    assert first_copy["moderation_status"] == "draft"
    assert first_copy["title"] == "Satellite (Copy)"
    assert first_copy["description"] == "Original launch"
    assert first_copy["category"] == "Objects"
    assert first_copy["keywords"] == ["orbit", "space"]

    second_copy_response = client.post(f"/api/creator/emojis/{original['id']}/duplicate", headers=headers)
    assert second_copy_response.status_code == 201
    assert second_copy_response.json()["title"] == "Satellite (Copy 2)"

    with db_session(client) as session:
        duplicate_memberships = session.exec(
            select(CollectionEmoji).where(CollectionEmoji.emoji_id == first_copy["id"])
        ).all()
        assert duplicate_memberships == []


def test_profile_update_only_changes_authenticated_user_and_profile_exposes_bio(client: TestClient) -> None:
    owner_headers, owner_id = register_and_login(client, "profile-owner@example.com", display_name="Owner")
    other_headers, other_id = register_and_login(client, "profile-other@example.com", display_name="Other")

    patch_response = client.patch(
        "/api/users/me",
        json={
            "display_name": "Owner Updated",
            "avatar_url": "https://cdn.example.com/owner.png",
            "bio": "I collect sparkly reactions.",
        },
        headers=owner_headers,
    )
    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["display_name"] == "Owner Updated"
    assert body["bio"] == "I collect sparkly reactions."

    owner_profile = client.get(f"/api/users/{owner_id}", headers=owner_headers)
    assert owner_profile.status_code == 200
    assert owner_profile.json()["bio"] == "I collect sparkly reactions."

    with db_session(client) as session:
        other_user = session.get(User, other_id)
        assert other_user is not None
        assert other_user.display_name == "Other"
        assert other_user.bio is None

    other_profile = client.get(f"/api/users/{other_id}", headers=other_headers)
    assert other_profile.status_code == 200
    assert other_profile.json()["bio"] is None


def test_creator_analytics_counts_statuses_and_top_emojis(client: TestClient) -> None:
    headers, _ = register_and_login(client, "analytics@example.com")

    create_creator_emoji(client, headers, symbol="🗂️", title="Draft Metric", intent="draft")
    create_creator_emoji(client, headers, symbol="⏳", title="Pending Metric", intent="submit")
    rejected = create_creator_emoji(client, headers, symbol="🛑", title="Rejected Metric", intent="submit")
    older_top = create_creator_emoji(client, headers, symbol="🎖️", title="Older Top", intent="submit")
    newer_top = create_creator_emoji(client, headers, symbol="🏅", title="Newer Top", intent="submit")
    third = create_creator_emoji(client, headers, symbol="🥉", title="Third Place", intent="submit")

    reject_emoji(client, rejected["id"], reason="Missing polish")
    approve_emoji(client, older_top["id"])
    approve_emoji(client, newer_top["id"])
    approve_emoji(client, third["id"])

    like_emoji_many_times(client, older_top["id"], 2)
    like_emoji_many_times(client, newer_top["id"], 2)
    like_emoji_many_times(client, third["id"], 1)

    response = client.get("/api/creator/analytics", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["draft_count"] == 1
    assert body["pending_count"] == 1
    assert body["approved_count"] == 3
    assert body["rejected_count"] == 1
    assert body["total_likes_received"] == 5
    assert [item["title"] for item in body["top_emojis"]] == [
        "Newer Top",
        "Older Top",
        "Third Place",
    ]
