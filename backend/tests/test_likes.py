from fastapi.testclient import TestClient

from tests.helpers import approve_emoji


def auth_headers(client: TestClient, email: str = "liker@example.com") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "SecretPwd123!", "display_name": "Liker"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": email, "password": "SecretPwd123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def create_emoji(client: TestClient, headers: dict, symbol: str = "🧪", title: str = "Test") -> int:
    resp = client.post(
        "/api/emojis",
        json={"symbol": symbol, "title": title, "keywords": ["test"]},
        headers=headers,
    )
    emoji_id = resp.json()["id"]
    approve_emoji(client, emoji_id)
    return emoji_id


# --- Like endpoint tests ---


def test_like_emoji(client: TestClient) -> None:
    headers = auth_headers(client)
    emoji_id = create_emoji(client, headers)

    resp = client.post(f"/api/emojis/{emoji_id}/like", headers=headers)
    assert resp.status_code == 201


def test_like_emoji_idempotent(client: TestClient) -> None:
    headers = auth_headers(client)
    emoji_id = create_emoji(client, headers)

    client.post(f"/api/emojis/{emoji_id}/like", headers=headers)
    resp = client.post(f"/api/emojis/{emoji_id}/like", headers=headers)
    assert resp.status_code == 200


def test_unlike_emoji(client: TestClient) -> None:
    headers = auth_headers(client)
    emoji_id = create_emoji(client, headers)

    client.post(f"/api/emojis/{emoji_id}/like", headers=headers)
    resp = client.delete(f"/api/emojis/{emoji_id}/like", headers=headers)
    assert resp.status_code == 204


def test_unlike_not_liked(client: TestClient) -> None:
    headers = auth_headers(client)
    emoji_id = create_emoji(client, headers)

    resp = client.delete(f"/api/emojis/{emoji_id}/like", headers=headers)
    assert resp.status_code == 204


def test_like_requires_auth(client: TestClient) -> None:
    headers = auth_headers(client)
    emoji_id = create_emoji(client, headers)

    resp = client.post(f"/api/emojis/{emoji_id}/like")
    assert resp.status_code == 401


def test_like_nonexistent_emoji(client: TestClient) -> None:
    headers = auth_headers(client)

    resp = client.post("/api/emojis/99999/like", headers=headers)
    assert resp.status_code == 404


# --- List endpoint with like data ---


def test_like_count_in_list(client: TestClient) -> None:
    headers_a = auth_headers(client, email="a@example.com")
    headers_b = auth_headers(client, email="b@example.com")
    emoji_id = create_emoji(client, headers_a)

    client.post(f"/api/emojis/{emoji_id}/like", headers=headers_a)
    client.post(f"/api/emojis/{emoji_id}/like", headers=headers_b)

    resp = client.get("/api/emojis")
    items = resp.json()["items"]
    item = next(i for i in items if i["id"] == emoji_id)
    assert item["like_count"] == 2


def test_is_liked_in_list(client: TestClient) -> None:
    headers = auth_headers(client)
    emoji_id = create_emoji(client, headers)

    client.post(f"/api/emojis/{emoji_id}/like", headers=headers)

    resp = client.get("/api/emojis", headers=headers)
    item = next(i for i in resp.json()["items"] if i["id"] == emoji_id)
    assert item["is_liked"] is True

    # Without auth, is_liked should be False
    resp = client.get("/api/emojis")
    item = next(i for i in resp.json()["items"] if i["id"] == emoji_id)
    assert item["is_liked"] is False


def test_sort_popular(client: TestClient) -> None:
    headers_a = auth_headers(client, email="pop_a@example.com")
    headers_b = auth_headers(client, email="pop_b@example.com")

    less_popular = create_emoji(client, headers_a, symbol="🥈", title="Silver")
    more_popular = create_emoji(client, headers_a, symbol="🥇", title="Gold")

    # Gold gets 2 likes, Silver gets 0
    client.post(f"/api/emojis/{more_popular}/like", headers=headers_a)
    client.post(f"/api/emojis/{more_popular}/like", headers=headers_b)

    resp = client.get("/api/emojis?sort=popular")
    items = resp.json()["items"]
    ids = [i["id"] for i in items]
    assert ids.index(more_popular) < ids.index(less_popular)


def test_favorites_filter(client: TestClient) -> None:
    headers = auth_headers(client)
    liked_id = create_emoji(client, headers, symbol="⭐", title="Star")
    create_emoji(client, headers, symbol="🔵", title="Blue")

    client.post(f"/api/emojis/{liked_id}/like", headers=headers)

    resp = client.get("/api/emojis?favorites=true", headers=headers)
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == liked_id


def test_favorites_without_auth(client: TestClient) -> None:
    resp = client.get("/api/emojis?favorites=true")
    items = resp.json()["items"]
    # Without auth, favorites filter is ignored — returns all emojis
    assert isinstance(items, list)
