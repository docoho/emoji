from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import approve_emoji, reject_emoji, set_user_superuser


def register_and_login(
    client: TestClient,
    *,
    email: str,
    display_name: str = "Moderator",
) -> tuple[dict[str, str], int]:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "SecretPwd123!",
            "display_name": display_name,
        },
    )
    user_id = register_response.json()["id"]
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "SecretPwd123!"},
    )
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}, user_id


def submit_emoji(
    client: TestClient,
    headers: dict[str, str],
    *,
    symbol: str = "🛡️",
    title: str = "Shield",
    category: str | None = "Objects",
    keywords: list[str] | None = None,
) -> dict:
    response = client.post(
        "/api/emojis",
        json={
            "symbol": symbol,
            "title": title,
            "category": category,
            "keywords": keywords or ["test"],
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_submissions_start_pending_and_are_hidden_from_public_list(client: TestClient) -> None:
    headers, _ = register_and_login(client, email="creator@example.com", display_name="Creator")
    emoji = submit_emoji(client, headers, symbol="🧪", title="Pending Lab", category="Objects")

    assert emoji["moderation_status"] == "pending"

    public_list = client.get("/api/emojis", headers=headers)
    assert public_list.status_code == 200
    assert all(item["id"] != emoji["id"] for item in public_list.json()["items"])

    like_response = client.post(f"/api/emojis/{emoji['id']}/like", headers=headers)
    assert like_response.status_code == 404


def test_admin_queue_requires_authentication_and_superuser(client: TestClient) -> None:
    creator_headers, _ = register_and_login(client, email="creator2@example.com")
    submit_emoji(client, creator_headers, symbol="🚧", title="Under Review")

    unauthorized = client.get("/api/admin/emojis")
    assert unauthorized.status_code == 401

    regular_headers, _ = register_and_login(client, email="viewer@example.com")
    forbidden = client.get("/api/admin/emojis", headers=regular_headers)
    assert forbidden.status_code == 403


def test_admin_dashboard_requires_authentication_and_superuser(client: TestClient) -> None:
    unauthorized = client.get("/api/admin/dashboard")
    assert unauthorized.status_code == 401

    regular_headers, _ = register_and_login(client, email="dashboard-viewer@example.com")
    forbidden = client.get("/api/admin/dashboard", headers=regular_headers)
    assert forbidden.status_code == 403


def test_admin_dashboard_returns_platform_snapshot(client: TestClient) -> None:
    creator_headers, _ = register_and_login(
        client,
        email="dashboard-creator@example.com",
        display_name="Dashboard Creator",
    )
    reporter_headers, _ = register_and_login(
        client,
        email="dashboard-reporter@example.com",
        display_name="Dashboard Reporter",
    )
    admin_headers, admin_id = register_and_login(
        client,
        email="dashboard-admin@example.com",
        display_name="Dashboard Admin",
    )
    set_user_superuser(client, admin_id)

    pending = submit_emoji(client, creator_headers, symbol="🧭", title="Needs Review", category="Travel")
    approved = submit_emoji(client, creator_headers, symbol="🍜", title="Public Noodles", category="Food")
    rejected = submit_emoji(client, creator_headers, symbol="🧊", title="Rejected Ice", category="Objects")
    approve_emoji(client, approved["id"], moderated_by_id=admin_id)
    reject_emoji(client, rejected["id"], reason="Too cold", moderated_by_id=admin_id)

    like_response = client.post(f"/api/emojis/{approved['id']}/like", headers=reporter_headers)
    assert like_response.status_code == 201

    comment_response = client.post(
        f"/api/emojis/{approved['id']}/comments",
        json={"body": "Useful in the gallery."},
        headers=reporter_headers,
    )
    assert comment_response.status_code == 201

    report_response = client.post(
        f"/api/emojis/{approved['id']}/reports",
        json={"reason": "other", "details": "Worth checking."},
        headers=reporter_headers,
    )
    assert report_response.status_code == 201

    response = client.get("/api/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()

    assert body["total_users"] == 3
    assert body["active_users"] == 3
    assert body["superuser_count"] == 1
    assert body["total_emojis"] == 3
    assert body["pending_emojis"] == 1
    assert body["approved_emojis"] == 1
    assert body["rejected_emojis"] == 1
    assert body["total_likes"] == 1
    assert body["total_comments"] == 1
    assert body["open_reports"] == 1
    assert body["new_users_7d"] == 3
    assert body["new_emojis_7d"] == 3
    assert body["new_reports_7d"] == 1
    assert body["emoji_status_counts"] == [
        {"status": "draft", "count": 0},
        {"status": "pending", "count": 1},
        {"status": "approved", "count": 1},
        {"status": "rejected", "count": 1},
    ]
    assert body["report_status_counts"] == [
        {"status": "open", "count": 1},
        {"status": "dismissed", "count": 0},
        {"status": "actioned", "count": 0},
    ]
    assert body["top_categories"] == [{"category": "Food", "count": 1}]
    assert body["recent_pending_emojis"][0]["id"] == pending["id"]
    assert body["recent_pending_emojis"][0]["submitter_name"] == "Dashboard Creator"
    assert body["recent_open_reports"][0]["emoji_id"] == approved["id"]
    assert body["recent_open_reports"][0]["reporter_name"] == "Dashboard Reporter"


def test_admin_queue_lists_pending_items_and_supports_filters(client: TestClient) -> None:
    creator_headers, creator_id = register_and_login(client, email="creator3@example.com", display_name="Queue User")
    admin_headers, admin_id = register_and_login(client, email="admin@example.com", display_name="Admin User")
    set_user_superuser(client, admin_id)

    first = submit_emoji(client, creator_headers, symbol="🍏", title="Green Apple", category="Food")
    second = submit_emoji(client, creator_headers, symbol="🌲", title="Pine Tree", category="Nature")

    queue = client.get("/api/admin/emojis", headers=admin_headers)
    assert queue.status_code == 200
    body = queue.json()
    assert body["total"] == 2
    assert [item["id"] for item in body["items"]] == [second["id"], first["id"]]

    filtered = client.get(
        f"/api/admin/emojis?status=pending&search=apple&category=Food&submitter_id={creator_id}&limit=1&offset=0",
        headers=admin_headers,
    )
    assert filtered.status_code == 200
    filtered_body = filtered.json()
    assert filtered_body["total"] == 1
    assert len(filtered_body["items"]) == 1
    assert filtered_body["items"][0]["title"] == "Green Apple"
    assert filtered_body["items"][0]["submitter_name"] == "Queue User"


def test_approve_makes_emoji_publicly_visible(client: TestClient) -> None:
    creator_headers, _ = register_and_login(client, email="creator4@example.com")
    admin_headers, admin_id = register_and_login(client, email="admin2@example.com", display_name="Approver")
    set_user_superuser(client, admin_id)
    emoji = submit_emoji(client, creator_headers, symbol="🎯", title="Approved Target")

    response = client.patch(
        f"/api/admin/emojis/{emoji['id']}/moderation",
        json={"status": "approved", "reason": "not used"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["moderation_status"] == "approved"
    assert body["moderation_reason"] is None
    assert body["moderated_by_id"] == admin_id

    public_list = client.get("/api/emojis")
    assert any(item["id"] == emoji["id"] for item in public_list.json()["items"])


def test_reject_hides_emoji_and_stores_internal_reason(client: TestClient) -> None:
    creator_headers, _ = register_and_login(client, email="creator5@example.com")
    admin_headers, admin_id = register_and_login(client, email="admin3@example.com", display_name="Reviewer")
    set_user_superuser(client, admin_id)
    emoji = submit_emoji(client, creator_headers, symbol="🪫", title="Battery Low")

    response = client.patch(
        f"/api/admin/emojis/{emoji['id']}/moderation",
        json={"status": "rejected", "reason": "Duplicate concept"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["moderation_status"] == "rejected"
    assert body["moderation_reason"] == "Duplicate concept"

    public_list = client.get("/api/emojis")
    assert all(item["id"] != emoji["id"] for item in public_list.json()["items"])

    rejected_queue = client.get("/api/admin/emojis?status=rejected", headers=admin_headers)
    rejected_item = rejected_queue.json()["items"][0]
    assert rejected_item["id"] == emoji["id"]
    assert rejected_item["moderation_reason"] == "Duplicate concept"


def test_reapproving_rejected_emoji_restores_visibility(client: TestClient) -> None:
    creator_headers, _ = register_and_login(client, email="creator6@example.com")
    admin_headers, admin_id = register_and_login(client, email="admin4@example.com")
    set_user_superuser(client, admin_id)
    emoji = submit_emoji(client, creator_headers, symbol="🛰️", title="Satellite")

    reject_response = client.patch(
        f"/api/admin/emojis/{emoji['id']}/moderation",
        json={"status": "rejected", "reason": "Needs revision"},
        headers=admin_headers,
    )
    assert reject_response.status_code == 200

    approve_response = client.patch(
        f"/api/admin/emojis/{emoji['id']}/moderation",
        json={"status": "approved", "reason": None},
        headers=admin_headers,
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["moderation_reason"] is None

    public_list = client.get("/api/emojis")
    assert any(item["id"] == emoji["id"] for item in public_list.json()["items"])


def test_public_list_excludes_rejected_but_keeps_approved_items_in_popular_and_favorites(
    client: TestClient,
) -> None:
    creator_headers, _ = register_and_login(client, email="creator7@example.com")
    viewer_headers, _ = register_and_login(client, email="viewer2@example.com")

    approved = submit_emoji(client, creator_headers, symbol="🏆", title="Winner")
    hidden = submit_emoji(client, creator_headers, symbol="🫥", title="Ghost")
    approve_emoji(client, approved["id"])
    reject_emoji(client, hidden["id"], reason="Not a fit")

    client.post(f"/api/emojis/{approved['id']}/like", headers=viewer_headers)

    popular = client.get("/api/emojis?sort=popular", headers=viewer_headers)
    popular_ids = [item["id"] for item in popular.json()["items"]]
    assert approved["id"] in popular_ids
    assert hidden["id"] not in popular_ids

    favorites = client.get("/api/emojis?favorites=true", headers=viewer_headers)
    favorite_ids = [item["id"] for item in favorites.json()["items"]]
    assert favorite_ids == [approved["id"]]


def test_update_approved_emoji_resets_moderation_to_pending(client: TestClient) -> None:
    """Editing any user-visible field on an APPROVED emoji must send it back to PENDING.

    Without this, a user could submit benign content, get approved, then edit
    to something offensive while keeping public visibility.
    """
    headers, _ = register_and_login(client, email="creator-edit@example.com")
    emoji = submit_emoji(client, headers, symbol="🌱", title="Sprout")
    approve_emoji(client, emoji["id"])

    # User edits the title — content has changed, must re-moderate
    resp = client.put(
        f"/api/emojis/{emoji['id']}",
        json={"title": "Sprout v2"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["moderation_status"] == "pending"
    assert body["title"] == "Sprout v2"

    # Public listing should no longer include it
    public = client.get("/api/emojis")
    assert all(item["id"] != emoji["id"] for item in public.json()["items"])


def test_update_pending_emoji_does_not_change_moderation_status(client: TestClient) -> None:
    """Editing a PENDING/DRAFT/REJECTED emoji should not flip status."""
    headers, _ = register_and_login(client, email="creator-pending@example.com")
    emoji = submit_emoji(client, headers, symbol="🪴", title="Plant")
    # Stays in default 'pending' state — no approve_emoji call.

    resp = client.put(
        f"/api/emojis/{emoji['id']}",
        json={"description": "Edited description"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["moderation_status"] == "pending"


def test_creator_update_approved_emoji_resets_moderation(client: TestClient) -> None:
    """Same policy applies on the creator-dashboard update endpoint."""
    headers, _ = register_and_login(client, email="creator-dashboard@example.com")
    emoji = submit_emoji(client, headers, symbol="🛰️", title="Satellite")
    approve_emoji(client, emoji["id"])

    resp = client.put(
        f"/api/creator/emojis/{emoji['id']}",
        json={"keywords": ["space", "orbit"]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["moderation_status"] == "pending"
