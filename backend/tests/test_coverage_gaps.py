"""Tests for functions that were previously uncovered."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.core.oauth import (
    create_oauth_state_token,
    validate_redirect_url,
    verify_oauth_state_token,
)
from app.core.oauth_codes import _OAuthCodeStore
from tests.helpers import approve_emoji


# ── Helpers ──────────────────────────────────────────────────────────────────


def _register_and_login(
    client: TestClient, email: str = "user@example.com", password: str = "SecretPwd123!"
) -> dict[str, str]:
    client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "display_name": "Tester",
    })
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_emoji(client: TestClient, headers: dict, symbol: str, title: str) -> dict:
    resp = client.post("/api/emojis", json={
        "symbol": symbol,
        "title": title,
        "keywords": ["test"],
    }, headers=headers)
    assert resp.status_code == 201
    emoji = resp.json()
    approve_emoji(client, emoji["id"])
    return emoji


# ── validate_redirect_url ────────────────────────────────────────────────────


class TestValidateRedirectUrl:
    """Open redirect prevention — security-critical."""

    def test_valid_path(self):
        assert validate_redirect_url("/dashboard") == "/dashboard"

    def test_root_path(self):
        assert validate_redirect_url("/") == "/"

    def test_nested_path(self):
        assert validate_redirect_url("/auth/callback?foo=bar") == "/auth/callback?foo=bar"

    def test_protocol_relative_url_blocked(self):
        assert validate_redirect_url("//evil.com") == "/"

    def test_absolute_url_blocked(self):
        assert validate_redirect_url("https://evil.com") == "/"

    def test_embedded_protocol_blocked(self):
        assert validate_redirect_url("/foo://bar") == "/"

    def test_empty_string_returns_root(self):
        assert validate_redirect_url("") == "/"

    def test_none_returns_root(self):
        assert validate_redirect_url(None) == "/"

    def test_whitespace_stripped(self):
        assert validate_redirect_url("  /dashboard  ") == "/dashboard"

    def test_no_leading_slash_blocked(self):
        assert validate_redirect_url("dashboard") == "/"


# ── OAuth state tokens ───────────────────────────────────────────────────────


class TestOAuthStateTokens:

    def test_roundtrip(self):
        token = create_oauth_state_token("/profile")
        redirect = verify_oauth_state_token(token)
        assert redirect == "/profile"

    def test_default_redirect(self):
        token = create_oauth_state_token()
        redirect = verify_oauth_state_token(token)
        assert redirect == "/"

    def test_invalid_token_returns_none(self):
        assert verify_oauth_state_token("garbage-token") is None

    def test_tampered_token_returns_none(self):
        token = create_oauth_state_token("/ok")
        assert verify_oauth_state_token(token + "tampered") is None

    def test_expired_token_returns_none(self):
        token = create_oauth_state_token("/expired")
        time.sleep(2)
        assert verify_oauth_state_token(token, max_age=1) is None


# ── OAuthCodeStore expiry ────────────────────────────────────────────────────


class TestOAuthCodeStoreExpiry:

    def test_expired_code_returns_none(self):
        store = _OAuthCodeStore(ttl_seconds=0)
        code = store.create("jwt-abc")
        # Code expires immediately (ttl=0)
        time.sleep(0.01)
        assert store.exchange(code) is None


# ── PUT /api/emojis/{id} (update_emoji) ─────────────────────────────────────


class TestUpdateEmoji:

    def test_update_own_emoji(self, client: TestClient):
        headers = _register_and_login(client, "updater@example.com")
        emoji = _create_emoji(client, headers, "🔧", "Wrench")

        resp = client.put(f"/api/emojis/{emoji['id']}", json={
            "title": "Wrench Updated",
            "description": "A useful tool",
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Wrench Updated"
        assert resp.json()["description"] == "A useful tool"

    def test_update_nonexistent_emoji_404(self, client: TestClient):
        headers = _register_and_login(client, "updater2@example.com")
        resp = client.put("/api/emojis/99999", json={"title": "Nope"}, headers=headers)
        assert resp.status_code == 404

    def test_update_other_user_emoji_403(self, client: TestClient):
        owner_headers = _register_and_login(client, "owner@example.com")
        other_headers = _register_and_login(client, "other@example.com")
        emoji = _create_emoji(client, owner_headers, "🔒", "Lock")

        resp = client.put(f"/api/emojis/{emoji['id']}", json={
            "title": "Hacked",
        }, headers=other_headers)
        assert resp.status_code == 403

    def test_update_requires_auth(self, client: TestClient):
        resp = client.put("/api/emojis/1", json={"title": "No Auth"})
        assert resp.status_code == 401


# ── GET /api/emojis search/filter/sort ───────────────────────────────────────


class TestListEmojisQueryParams:

    @pytest.fixture(autouse=True)
    def _seed_emojis(self, client: TestClient):
        headers = _register_and_login(client, "seeder@example.com")
        _create_emoji(client, headers, "🍎", "Apple")
        banana = client.post("/api/emojis", json={
            "symbol": "🍌", "title": "Banana", "category": "Food",
            "keywords": ["fruit", "yellow"],
        }, headers=headers)
        dog = client.post("/api/emojis", json={
            "symbol": "🐶", "title": "Dog", "category": "Nature",
            "keywords": ["animal", "pet"],
        }, headers=headers)
        approve_emoji(client, banana.json()["id"])
        approve_emoji(client, dog.json()["id"])

    def test_search_by_title(self, client: TestClient):
        resp = client.get("/api/emojis", params={"search": "banana"})
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["title"] == "Banana"

    def test_search_by_keyword(self, client: TestClient):
        resp = client.get("/api/emojis", params={"search": "yellow"})
        items = resp.json()["items"]
        assert any(item["title"] == "Banana" for item in items)

    def test_filter_by_category(self, client: TestClient):
        resp = client.get("/api/emojis", params={"category": "Nature"})
        items = resp.json()["items"]
        assert all(item["title"] == "Dog" for item in items)

    def test_sort_title_asc(self, client: TestClient):
        resp = client.get("/api/emojis", params={"sort": "title_asc"})
        titles = [item["title"] for item in resp.json()["items"]]
        assert titles == sorted(titles)

    def test_pagination(self, client: TestClient):
        resp = client.get("/api/emojis", params={"limit": 1, "offset": 0})
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == 3

    def test_popular_sort_with_pagination(self, client: TestClient):
        """Most-liked emoji should appear on page 1 even if it's not the most recent."""
        headers = _register_and_login(client, "liker@example.com")

        # Like only "Apple" (the oldest emoji) — it should rank first in popular sort
        emojis_resp = client.get("/api/emojis", params={"sort": "title_asc"})
        apple = next(e for e in emojis_resp.json()["items"] if e["title"] == "Apple")
        client.post(f"/api/emojis/{apple['id']}/like", headers=headers)

        # Request page 1 with limit=1 and sort=popular
        resp = client.get("/api/emojis", params={"sort": "popular", "limit": 1, "offset": 0})
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["title"] == "Apple", "Most-liked emoji should be first on page 1"


# ── Login edge case: OAuth-only user ─────────────────────────────────────────


# TODO(human): Implement the test for OAuth-only user login attempt.
# This tests the branch at auth.py where a user has no password.
# Per our anti-enumeration policy, the response must not reveal that the
# account exists as OAuth-only — it returns the same generic 401 as a
# non-existent email or wrong password.
def test_login_oauth_only_user_rejected(client: TestClient):
    from app.db import get_session
    from app.models import User

    # Create a user with no password (OAuth-only)
    session = next(client.app.dependency_overrides[get_session]())
    oauth_user = User(
        email="google-only@example.com",
        hashed_password=None,
        google_id="google-123",
        oauth_provider="google",
        display_name="Google User",
    )
    session.add(oauth_user)
    session.commit()

    resp = client.post("/api/auth/login", json={
        "email": "google-only@example.com",
        "password": "AnyPassword1!",
    })
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert detail == "Incorrect email or password"
    assert "Google" not in detail
    assert "Sign in with Google" not in detail


# ── get_optional_user ────────────────────────────────────────────────────────


class TestOptionalUser:

    def test_anonymous_can_list_emojis(self, client: TestClient):
        """Unauthenticated requests should still return emojis (can_delete=False)."""
        headers = _register_and_login(client, "creator@example.com")
        _create_emoji(client, headers, "🎯", "Target")

        resp = client.get("/api/emojis")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        assert all(item["can_delete"] is False for item in items)

    def test_authenticated_sees_can_delete(self, client: TestClient):
        """Authenticated user should see can_delete=True on own emojis."""
        headers = _register_and_login(client, "candelete@example.com")
        _create_emoji(client, headers, "🎨", "Art")

        resp = client.get("/api/emojis", headers=headers)
        items = resp.json()["items"]
        own = [i for i in items if i["title"] == "Art"]
        assert own[0]["can_delete"] is True

    def test_invalid_token_treated_as_anonymous(self, client: TestClient):
        """Bad tokens should degrade gracefully to anonymous, not 401."""
        headers = _register_and_login(client, "tokentest@example.com")
        _create_emoji(client, headers, "🧩", "Puzzle")

        resp = client.get("/api/emojis", headers={"Authorization": "Bearer bad-token"})
        assert resp.status_code == 200
        assert all(item["can_delete"] is False for item in resp.json()["items"])
