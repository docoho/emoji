from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.ratelimit import login_limiter, register_limiter
from app.db import get_session
from app.models import User
from tests.helpers import approve_emoji


def collection_label(collection: dict) -> str:
    return collection.get("name") or collection.get("title") or collection.get("slug") or ""


def register_and_login(client: TestClient, email: str) -> tuple[dict[str, str], int]:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "SecretPwd123!",
            "display_name": "Collector",
        },
    )
    user_id = register_response.json()["id"]
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "SecretPwd123!"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
    return headers, user_id


def create_emoji(
    client: TestClient,
    headers: dict[str, str],
    *,
    symbol: str = "🧪",
    title: str = "Test Emoji",
    keywords: list[str] | None = None,
    category: str | None = None,
) -> dict:
    response = client.post(
        "/api/emojis",
        json={
            "symbol": symbol,
            "title": title,
            "keywords": keywords or ["test"],
            "category": category,
        },
        headers=headers,
    )
    assert response.status_code == 201
    emoji = response.json()
    approve_emoji(client, emoji["id"])
    return emoji


def create_collection(
    client: TestClient,
    headers: dict[str, str],
    *,
    title: str,
    description: str = "A test collection",
    kind: str = "personal",
) -> dict:
    for payload in (
        {"name": title, "description": description, "kind": kind},
        {"title": title, "description": description, "kind": kind},
        {"name": title, "kind": kind},
        {"title": title, "kind": kind},
    ):
        response = client.post("/api/collections", json=payload, headers=headers)
        if response.status_code != 422:
            assert response.status_code in (200, 201)
            return response.json()
    assert response.status_code != 422
    return response.json()


def update_user(
    client: TestClient,
    user_id: int,
    *,
    avatar_url: str | None = None,
    display_name: str | None = None,
) -> None:
    session_gen = client.app.dependency_overrides[get_session]()
    session = next(session_gen)
    try:
        user = session.get(User, user_id)
        assert user is not None
        if avatar_url is not None:
            user.avatar_url = avatar_url
        if display_name is not None:
            user.display_name = display_name
        session.add(user)
        session.commit()
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass


def test_user_profile_includes_collections_additively(client: TestClient) -> None:
    headers, user_id = register_and_login(client, email="profile@example.com")
    emoji = create_emoji(client, headers, symbol="🏷️", title="Label")
    first_collection = create_collection(client, headers, title="Pinned", kind="public")
    second_collection = create_collection(client, headers, title="Saved")

    profile_response = client.get(f"/api/users/{user_id}", headers=headers)
    assert profile_response.status_code == 200
    profile = profile_response.json()

    assert profile["emoji_count"] == 1
    assert profile["total_likes_received"] == 0
    assert isinstance(profile["emojis"], list)
    assert len(profile["emojis"]) == 1
    assert profile["emojis"][0]["id"] == emoji["id"]
    assert profile["emojis"][0]["title"] == "Label"

    assert "collection_count" in profile
    assert "collections" in profile
    assert profile["collection_count"] == 2
    assert len(profile["collections"]) == 2
    assert {collection_label(item) for item in profile["collections"]} == {"Pinned", "Saved"}
    assert profile["stats"] == {
        "emoji_count": 1,
        "total_likes_received": 0,
        "collection_count": 2,
        "public_collection_count": 1,
        "categories_used_count": 0,
    }
    assert len(profile["achievements"]) == 6
    assert profile["highlights"]["top_emoji"]["id"] == emoji["id"]
    assert [collection_label(item) for item in profile["highlights"]["recent_public_collections"]] == [
        "Pinned"
    ]

    # Keep a small regression check on the collection labels to ensure the profile
    # payload remains additive rather than reshaped.
    assert first_collection["id"] in {item["id"] for item in profile["collections"]}
    assert second_collection["id"] in {item["id"] for item in profile["collections"]}


def test_creator_profile_returns_avatar_url(client: TestClient) -> None:
    headers, user_id = register_and_login(client, email="avatar@example.com")
    update_user(client, user_id, avatar_url="https://cdn.example.com/avatar.png")

    profile_response = client.get(f"/api/users/{user_id}", headers=headers)

    assert profile_response.status_code == 200
    assert profile_response.json()["avatar_url"] == "https://cdn.example.com/avatar.png"


def test_anonymous_viewer_sees_only_public_creator_collections(client: TestClient) -> None:
    headers, user_id = register_and_login(client, email="public-only@example.com")
    create_collection(client, headers, title="Public Picks", kind="public")
    create_collection(client, headers, title="Private Drafts", kind="personal")

    profile_response = client.get(f"/api/users/{user_id}")

    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["collection_count"] == 1
    assert profile["stats"]["collection_count"] == 2
    assert profile["stats"]["public_collection_count"] == 1
    assert [collection_label(item) for item in profile["collections"]] == ["Public Picks"]
    assert all(item["kind"] == "public" for item in profile["collections"])


def test_authenticated_non_owner_sees_only_public_creator_collections(client: TestClient) -> None:
    creator_headers, user_id = register_and_login(client, email="creator-visible@example.com")
    viewer_headers, _ = register_and_login(client, email="viewer@example.com")
    create_collection(client, creator_headers, title="Showcase", kind="public")
    create_collection(client, creator_headers, title="Workbench", kind="personal")

    profile_response = client.get(f"/api/users/{user_id}", headers=viewer_headers)

    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["collection_count"] == 1
    assert profile["stats"]["collection_count"] == 2
    assert profile["stats"]["public_collection_count"] == 1
    assert [collection_label(item) for item in profile["collections"]] == ["Showcase"]


def test_creator_sees_public_and_personal_collections_on_own_profile(client: TestClient) -> None:
    headers, user_id = register_and_login(client, email="owner-view@example.com")
    create_collection(client, headers, title="Public Shelf", kind="public")
    create_collection(client, headers, title="Private Shelf", kind="personal")

    profile_response = client.get(f"/api/users/{user_id}", headers=headers)

    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["collection_count"] == 2
    assert {collection_label(item) for item in profile["collections"]} == {
        "Public Shelf",
        "Private Shelf",
    }


def test_profile_like_totals_and_viewer_specific_emoji_flags(client: TestClient) -> None:
    creator_headers, creator_id = register_and_login(client, email="creator-flags@example.com")
    viewer_headers, _ = register_and_login(client, email="fan@example.com")
    emoji = create_emoji(client, creator_headers, symbol="✨", title="Sparkle")

    like_response = client.post(f"/api/emojis/{emoji['id']}/like", headers=viewer_headers)
    assert like_response.status_code == 201

    viewer_profile_response = client.get(f"/api/users/{creator_id}", headers=viewer_headers)
    assert viewer_profile_response.status_code == 200
    viewer_profile = viewer_profile_response.json()

    assert viewer_profile["total_likes_received"] == 1
    assert viewer_profile["collection_count"] == len(viewer_profile["collections"])
    assert viewer_profile["emojis"][0]["is_liked"] is True
    assert viewer_profile["emojis"][0]["can_delete"] is False

    creator_profile_response = client.get(f"/api/users/{creator_id}", headers=creator_headers)
    assert creator_profile_response.status_code == 200
    creator_profile = creator_profile_response.json()

    assert creator_profile["total_likes_received"] == 1
    assert creator_profile["emojis"][0]["is_liked"] is False
    assert creator_profile["emojis"][0]["can_delete"] is True
    assert viewer_profile["stats"]["total_likes_received"] == 1
    assert creator_profile["stats"]["total_likes_received"] == 1


def test_zero_state_profile_returns_default_stats_and_locked_achievements(client: TestClient) -> None:
    headers, user_id = register_and_login(client, email="zero-state@example.com")

    profile_response = client.get(f"/api/users/{user_id}", headers=headers)

    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["emojis"] == []
    assert profile["collections"] == []
    assert profile["stats"] == {
        "emoji_count": 0,
        "total_likes_received": 0,
        "collection_count": 0,
        "public_collection_count": 0,
        "categories_used_count": 0,
    }
    assert profile["highlights"] == {
        "top_emoji": None,
        "recent_public_collections": [],
    }
    assert all(item["earned"] is False for item in profile["achievements"])
    assert {item["id"] for item in profile["achievements"]} == {
        "first_submission",
        "emoji_trio",
        "liked_creator",
        "crowd_favorite",
        "public_curator",
        "variety_pack",
    }


def test_profile_stats_achievements_and_highlights_are_derived_from_existing_data(
    client: TestClient,
) -> None:
    creator_headers, creator_id = register_and_login(client, email="achievements@example.com")
    viewer_headers, _ = register_and_login(client, email="achievements-viewer@example.com")

    newest_top = create_emoji(
        client,
        creator_headers,
        symbol="🔥",
        title="Fire",
        category="Nature",
    )
    create_emoji(
        client,
        creator_headers,
        symbol="🍔",
        title="Burger",
        category="Food",
    )
    third = create_emoji(
        client,
        creator_headers,
        symbol="⚽",
        title="Goal",
        category="Activities",
    )

    public_one = create_collection(client, creator_headers, title="Launch Picks", kind="public")
    create_collection(client, creator_headers, title="Private Bench", kind="personal")
    public_two = create_collection(client, creator_headers, title="Festival Set", kind="public")
    public_three = create_collection(client, creator_headers, title="Victory Lap", kind="public")
    create_collection(client, creator_headers, title="Deep Archive", kind="public")

    for _ in range(10):
        register_limiter.reset()
        login_limiter.reset()
        liker_headers, _ = register_and_login(client, email=f"fan{_}@example.com")
        liked_emoji_id = newest_top["id"] if _ < 5 else third["id"]
        like_response = client.post(f"/api/emojis/{liked_emoji_id}/like", headers=liker_headers)
        assert like_response.status_code == 201

    profile_response = client.get(f"/api/users/{creator_id}", headers=viewer_headers)

    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["stats"] == {
        "emoji_count": 3,
        "total_likes_received": 10,
        "collection_count": 5,
        "public_collection_count": 4,
        "categories_used_count": 3,
    }
    achievements = {item["id"]: item for item in profile["achievements"]}
    assert all(item["earned"] is True for item in achievements.values())
    assert achievements["crowd_favorite"]["progress_current"] == 10
    assert achievements["variety_pack"]["progress_current"] == 3
    assert profile["highlights"]["top_emoji"]["id"] == third["id"]
    assert profile["highlights"]["top_emoji"]["is_liked"] is False
    assert [
        collection_label(item) for item in profile["highlights"]["recent_public_collections"]
    ] == ["Deep Archive", "Victory Lap", "Festival Set"]
    assert public_one["id"] not in {
        item["id"] for item in profile["highlights"]["recent_public_collections"]
    }
    assert public_two["id"] in {
        item["id"] for item in profile["highlights"]["recent_public_collections"]
    }
    assert public_three["id"] in {
        item["id"] for item in profile["highlights"]["recent_public_collections"]
    }


def test_profile_stats_ignore_blank_categories_and_top_emoji_uses_newest_tiebreaker(
    client: TestClient,
) -> None:
    creator_headers, creator_id = register_and_login(client, email="tiebreak@example.com")

    older = create_emoji(
        client,
        creator_headers,
        symbol="🧊",
        title="Ice",
        category="  ",
    )
    newer = create_emoji(
        client,
        creator_headers,
        symbol="🌊",
        title="Wave",
        category=None,
    )

    profile_response = client.get(f"/api/users/{creator_id}", headers=creator_headers)

    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["stats"]["categories_used_count"] == 0
    assert profile["highlights"]["top_emoji"]["id"] == newer["id"]
    assert profile["highlights"]["top_emoji"]["title"] != older["title"]
