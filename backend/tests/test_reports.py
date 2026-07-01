from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import approve_emoji, set_user_superuser


def auth_headers(client: TestClient, email: str) -> tuple[dict[str, str], int]:
    register_response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "SecretPwd123!", "display_name": email.split("@")[0]},
    )
    login_response = client.post("/api/auth/login", json={"email": email, "password": "SecretPwd123!"})
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}, register_response.json()["id"]


def create_public_emoji(client: TestClient, headers: dict[str, str], *, symbol: str, title: str) -> int:
    response = client.post(
        "/api/emojis",
        json={"symbol": symbol, "title": title, "keywords": ["reportable"]},
        headers=headers,
    )
    emoji_id = response.json()["id"]
    approve_emoji(client, emoji_id)
    return emoji_id


def test_report_requires_authentication(client: TestClient) -> None:
    creator_headers, _ = auth_headers(client, "report-creator@example.com")
    emoji_id = create_public_emoji(client, creator_headers, symbol="🚨", title="Report Target")

    response = client.post(f"/api/emojis/{emoji_id}/reports", json={"reason": "spam"})
    assert response.status_code == 401


def test_only_approved_emojis_can_be_reported(client: TestClient) -> None:
    creator_headers, _ = auth_headers(client, "pending-creator@example.com")
    reporter_headers, _ = auth_headers(client, "reporter@example.com")
    response = client.post(
        "/api/emojis",
        json={"symbol": "⏳", "title": "Pending Emoji", "keywords": ["pending"]},
        headers=creator_headers,
    )
    emoji_id = response.json()["id"]

    report = client.post(
        f"/api/emojis/{emoji_id}/reports",
        json={"reason": "misleading"},
        headers=reporter_headers,
    )
    assert report.status_code == 404


def test_duplicate_open_report_returns_existing_item(client: TestClient) -> None:
    creator_headers, _ = auth_headers(client, "duplicate-creator@example.com")
    reporter_headers, _ = auth_headers(client, "duplicate-reporter@example.com")
    emoji_id = create_public_emoji(client, creator_headers, symbol="📣", title="Duplicate Report")

    first = client.post(
        f"/api/emojis/{emoji_id}/reports",
        json={"reason": "spam", "details": "First note"},
        headers=reporter_headers,
    )
    second = client.post(
        f"/api/emojis/{emoji_id}/reports",
        json={"reason": "offensive", "details": "Second note"},
        headers=reporter_headers,
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["reason"] == "spam"


def test_admin_can_filter_and_update_reports(client: TestClient) -> None:
    creator_headers, _ = auth_headers(client, "admin-report-creator@example.com")
    reporter_headers, _ = auth_headers(client, "admin-report-reporter@example.com")
    admin_headers, admin_id = auth_headers(client, "admin-report@example.com")
    set_user_superuser(client, admin_id)

    emoji_id = create_public_emoji(client, creator_headers, symbol="🧯", title="Reportable Flame")
    created = client.post(
        f"/api/emojis/{emoji_id}/reports",
        json={"reason": "copyright", "details": "Looks copied"},
        headers=reporter_headers,
    )
    assert created.status_code == 201

    listing = client.get(
        "/api/admin/reports?status=open&reason=copyright&search=flame",
        headers=admin_headers,
    )
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["items"][0]["emoji_title"] == "Reportable Flame"

    updated = client.patch(
        f"/api/admin/reports/{created.json()['id']}",
        json={"status": "actioned", "admin_note": "Escalated for follow-up"},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "actioned"
    assert updated.json()["admin_note"] == "Escalated for follow-up"
    assert updated.json()["resolved_by_id"] == admin_id


def test_reporting_does_not_hide_public_emoji(client: TestClient) -> None:
    creator_headers, _ = auth_headers(client, "visibility-creator@example.com")
    reporter_headers, _ = auth_headers(client, "visibility-reporter@example.com")
    emoji_id = create_public_emoji(client, creator_headers, symbol="👀", title="Still Visible")

    report = client.post(
        f"/api/emojis/{emoji_id}/reports",
        json={"reason": "other", "details": "Needs another look"},
        headers=reporter_headers,
    )
    assert report.status_code == 201

    public_list = client.get("/api/emojis")
    assert emoji_id in [item["id"] for item in public_list.json()["items"]]
