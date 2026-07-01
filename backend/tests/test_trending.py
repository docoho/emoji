from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from app.core.ratelimit import login_limiter, register_limiter
from tests.helpers import approve_emoji, test_session as session_scope


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    register_limiter.reset()
    login_limiter.reset()
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "SecretPwd123!", "display_name": email.split("@")[0]},
    )
    response = client.post("/api/auth/login", json={"email": email, "password": "SecretPwd123!"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_public_emoji(
    client: TestClient,
    headers: dict[str, str],
    *,
    symbol: str,
    title: str,
    category: str = "Objects",
) -> int:
    response = client.post(
        "/api/emojis",
        json={"symbol": symbol, "title": title, "category": category, "keywords": ["phase1"]},
        headers=headers,
    )
    emoji_id = response.json()["id"]
    approve_emoji(client, emoji_id)
    return emoji_id


def set_like_timestamp_for_latest_like(client: TestClient, *, emoji_id: int, age_days: int) -> None:
    with session_scope(client) as session:
        from app.models import EmojiLike
        from sqlmodel import select

        like = session.exec(
            select(EmojiLike).where(EmojiLike.emoji_id == emoji_id).order_by(EmojiLike.id.desc())
        ).first()
        assert like is not None
        like.created_at = datetime.now(timezone.utc) - timedelta(days=age_days)
        session.add(like)
        session.commit()


def test_trending_week_prioritizes_recent_likes_over_lifetime(client: TestClient) -> None:
    creator = auth_headers(client, "creator-trend@example.com")
    weekly_winner = create_public_emoji(client, creator, symbol="🔥", title="Weekly Winner")
    old_favorite = create_public_emoji(client, creator, symbol="📦", title="Old Favorite")

    for index in range(2):
        liker = auth_headers(client, f"recent{index}@example.com")
        client.post(f"/api/emojis/{weekly_winner}/like", headers=liker)
        client.post(f"/api/emojis/{old_favorite}/like", headers=liker)
        set_like_timestamp_for_latest_like(client, emoji_id=weekly_winner, age_days=2)
        set_like_timestamp_for_latest_like(client, emoji_id=old_favorite, age_days=15)

    current_liker = auth_headers(client, "current@example.com")
    client.post(f"/api/emojis/{weekly_winner}/like", headers=current_liker)
    client.post(f"/api/emojis/{old_favorite}/like", headers=current_liker)
    set_like_timestamp_for_latest_like(client, emoji_id=old_favorite, age_days=2)

    response = client.get("/api/emojis?sort=trending_week")
    ids = [item["id"] for item in response.json()["items"]]
    assert ids.index(weekly_winner) < ids.index(old_favorite)


def test_trending_day_uses_lifetime_then_recency_tiebreakers(client: TestClient) -> None:
    creator = auth_headers(client, "creator-tiebreak@example.com")
    higher_lifetime = create_public_emoji(client, creator, symbol="🏅", title="Higher Lifetime")
    older_same_counts = create_public_emoji(client, creator, symbol="📜", title="Older Same Counts")
    newer_same_counts = create_public_emoji(client, creator, symbol="🆕", title="Newer Same Counts")

    client.post(f"/api/emojis/{higher_lifetime}/like", headers=auth_headers(client, "hl-recent@example.com"))
    set_like_timestamp_for_latest_like(client, emoji_id=higher_lifetime, age_days=0)
    client.post(f"/api/emojis/{higher_lifetime}/like", headers=auth_headers(client, "hl-old@example.com"))
    set_like_timestamp_for_latest_like(client, emoji_id=higher_lifetime, age_days=12)

    client.post(f"/api/emojis/{newer_same_counts}/like", headers=auth_headers(client, "new-recent@example.com"))
    set_like_timestamp_for_latest_like(client, emoji_id=newer_same_counts, age_days=0)

    client.post(f"/api/emojis/{older_same_counts}/like", headers=auth_headers(client, "old-recent@example.com"))
    set_like_timestamp_for_latest_like(client, emoji_id=older_same_counts, age_days=0)

    response = client.get("/api/emojis?sort=trending_day")
    titles = [item["title"] for item in response.json()["items"][:3]]
    assert titles == ["Higher Lifetime", "Newer Same Counts", "Older Same Counts"]


def test_top_month_paginates_after_ranking_and_keeps_zero_window_items(client: TestClient) -> None:
    creator = auth_headers(client, "creator-month@example.com")
    current_month = create_public_emoji(client, creator, symbol="📈", title="Current Month")
    older_lifetime = create_public_emoji(client, creator, symbol="🗃️", title="Older Lifetime")
    no_likes = create_public_emoji(client, creator, symbol="🫧", title="No Likes")

    client.post(f"/api/emojis/{current_month}/like", headers=auth_headers(client, "month-like@example.com"))
    set_like_timestamp_for_latest_like(client, emoji_id=current_month, age_days=10)

    client.post(f"/api/emojis/{older_lifetime}/like", headers=auth_headers(client, "older-like@example.com"))
    set_like_timestamp_for_latest_like(client, emoji_id=older_lifetime, age_days=45)

    page = client.get("/api/emojis?sort=top_month&limit=1&offset=1")
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 3
    assert body["items"][0]["id"] == older_lifetime

    full = client.get("/api/emojis?sort=top_month")
    ids = [item["id"] for item in full.json()["items"]]
    assert no_likes in ids


def test_trending_filters_work_with_favorites_search_and_category(client: TestClient) -> None:
    creator = auth_headers(client, "creator-filters@example.com")
    target = create_public_emoji(client, creator, symbol="🍣", title="Sushi Party", category="Food")
    other = create_public_emoji(client, creator, symbol="🌳", title="Forest Walk", category="Nature")
    viewer = auth_headers(client, "viewer-filters@example.com")

    client.post(f"/api/emojis/{target}/like", headers=viewer)
    client.post(f"/api/emojis/{other}/like", headers=viewer)
    set_like_timestamp_for_latest_like(client, emoji_id=target, age_days=1)
    set_like_timestamp_for_latest_like(client, emoji_id=other, age_days=20)

    response = client.get(
        "/api/emojis?sort=trending_week&favorites=true&search=sushi&category=Food",
        headers=viewer,
    )
    items = response.json()["items"]
    assert [item["id"] for item in items] == [target]


def test_popular_sort_orders_by_lifetime_likes_desc(client: TestClient) -> None:
    creator = auth_headers(client, "creator-popular@example.com")
    emoji_a = create_public_emoji(client, creator, symbol="🅰️", title="Emoji A")
    emoji_b = create_public_emoji(client, creator, symbol="🅱️", title="Emoji B")
    create_public_emoji(client, creator, symbol="🅲", title="Emoji C")

    for _ in range(5):
        liker = auth_headers(client, f"pop-a-{_}@example.com")
        client.post(f"/api/emojis/{emoji_a}/like", headers=liker)
    for _ in range(2):
        liker = auth_headers(client, f"pop-b-{_}@example.com")
        client.post(f"/api/emojis/{emoji_b}/like", headers=liker)

    response = client.get("/api/emojis?sort=popular")
    titles = [item["title"] for item in response.json()["items"]]
    assert titles.index("Emoji A") < titles.index("Emoji B") < titles.index("Emoji C")


def test_ranking_sql_pagination_works(client: TestClient) -> None:
    creator = auth_headers(client, "creator-page@example.com")
    emojis = []
    for i in range(5):
        eid = create_public_emoji(client, creator, symbol=str(i), title=f"Page Emoji {i}")
        emojis.append(eid)

    for i, eid in enumerate(emojis):
        for _ in range(5 - i):
            liker = auth_headers(client, f"page-{eid}-{_}@example.com")
            client.post(f"/api/emojis/{eid}/like", headers=liker)

    response = client.get("/api/emojis?sort=popular&limit=2&offset=2")
    body = response.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    ids = [item["id"] for item in body["items"]]
    assert ids == [emojis[2], emojis[3]]


def test_ranking_zero_likes_emojis_appear_last(client: TestClient) -> None:
    creator = auth_headers(client, "creator-zero@example.com")
    liked = create_public_emoji(client, creator, symbol="⭐", title="Liked One")
    create_public_emoji(client, creator, symbol="🕳️", title="Unliked One")

    liker = auth_headers(client, "zero-liker@example.com")
    client.post(f"/api/emojis/{liked}/like", headers=liker)

    response = client.get("/api/emojis?sort=trending_week")
    titles = [item["title"] for item in response.json()["items"]]
    assert titles.index("Liked One") < titles.index("Unliked One")
