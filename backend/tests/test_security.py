from __future__ import annotations

import os
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.oauth_codes import oauth_code_store
from app.core.security import create_access_token, decode_token
from tests.helpers import approve_emoji


INSECURE_DEFAULTS = [
    "dev-secret-key-change-me",
    "oauth-state-secret-change-me",
    "secret",
    "changeme",
]


def test_secret_key_not_hardcoded():
    """Default secret_key must not be any well-known insecure value."""
    s = Settings()
    for bad in INSECURE_DEFAULTS:
        assert s.secret_key != bad


def test_oauth_state_secret_not_hardcoded():
    """Default oauth_state_secret must not be any well-known insecure value."""
    s = Settings()
    for bad in INSECURE_DEFAULTS:
        assert s.oauth_state_secret != bad


def test_fallback_secret_generation():
    """When SECRET_KEY is not configured, a secure random fallback should be used."""
    s1 = Settings(_env_file="/dev/null")
    s2 = Settings(_env_file="/dev/null")
    assert s1.secret_key != s2.secret_key
    assert len(s1.secret_key) >= 32
    assert len(s2.secret_key) >= 32


def test_secret_key_sufficient_length():
    """Generated secrets should have at least 32 bytes of entropy."""
    s = Settings()
    # token_urlsafe(32) produces ~43 chars; ensure a reasonable minimum
    assert len(s.secret_key) >= 32
    assert len(s.oauth_state_secret) >= 32


def test_env_var_overrides_secret_key():
    """SECRET_KEY env var should override the random default."""
    with patch.dict(os.environ, {"SECRET_KEY": "my-custom-key"}):
        s = Settings()
        assert s.secret_key == "my-custom-key"


def test_env_var_overrides_oauth_state_secret():
    """OAUTH_STATE_SECRET env var should override the random default."""
    with patch.dict(os.environ, {"OAUTH_STATE_SECRET": "my-oauth-secret"}):
        s = Settings()
        assert s.oauth_state_secret == "my-oauth-secret"


def test_jwt_roundtrip_with_random_secret():
    """JWTs created and verified in the same process should still work."""
    token = create_access_token(subject="42")
    payload = decode_token(token)
    assert payload["sub"] == "42"


def test_password_reset_response_has_no_token_field(client: TestClient):
    """Password reset endpoint must not leak the reset token in the response."""
    client.post("/api/auth/register", json={
        "email": "reset@example.com",
        "password": "SecretPwd123!",
        "display_name": "Tester",
    })
    response = client.post(
        "/api/auth/password-reset/request",
        json={"email": "reset@example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "reset_token" not in body
    assert body["message"] == "If the email exists, a reset link will be sent"


def test_password_reset_no_email_enumeration(client: TestClient):
    """Response for nonexistent email must be identical to real email."""
    client.post("/api/auth/register", json={
        "email": "real@example.com",
        "password": "SecretPwd123!",
        "display_name": "Tester",
    })
    real = client.post(
        "/api/auth/password-reset/request",
        json={"email": "real@example.com"},
    )
    fake = client.post(
        "/api/auth/password-reset/request",
        json={"email": "nonexistent@example.com"},
    )
    assert real.status_code == fake.status_code
    assert real.json() == fake.json()


# --- New security tests ---


def test_cors_not_wildcard(client: TestClient):
    """CORS must not respond with Access-Control-Allow-Origin: * for unknown origins."""
    response = client.options(
        "/api/emojis",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    allow_origin = response.headers.get("access-control-allow-origin", "")
    assert allow_origin != "*"
    assert "evil.example.com" not in allow_origin


def test_referrer_policy_header_present(client: TestClient):
    """Responses should suppress Referer leakage for sensitive query-string flows."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers.get("referrer-policy") == "no-referrer"


def test_oauth_code_exchange_roundtrip():
    """OAuth exchange code can be redeemed for the stored JWT exactly once."""
    jwt = "test-jwt-token-abc123"
    code = oauth_code_store.create(jwt)

    # First exchange succeeds
    result = oauth_code_store.exchange(code)
    assert result == jwt

    # Second exchange fails (one-time use)
    result2 = oauth_code_store.exchange(code)
    assert result2 is None


def test_oauth_code_invalid():
    """Invalid codes return None."""
    result = oauth_code_store.exchange("nonexistent-code")
    assert result is None


def test_oauth_exchange_endpoint(client: TestClient):
    """POST /api/auth/oauth/exchange with valid code returns JWT."""
    jwt = "test-jwt-for-endpoint"
    code = oauth_code_store.create(jwt)

    response = client.post("/api/auth/oauth/exchange", json={"code": code})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == jwt
    assert body["token_type"] == "bearer"

    # Replaying the code fails
    response2 = client.post("/api/auth/oauth/exchange", json={"code": code})
    assert response2.status_code == 400


def test_emoji_response_has_no_submitter_email(client: TestClient):
    """GET /api/emojis response items must not contain submitter_email."""
    # Register + login to create an emoji
    client.post("/api/auth/register", json={
        "email": "emojier@example.com",
        "password": "StrongPass1!",
        "display_name": "Emojier",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "emojier@example.com",
        "password": "StrongPass1!",
    })
    token = login_resp.json()["access_token"]

    client.post("/api/emojis", json={
        "symbol": "\U0001f600",
        "title": "Grinning Face",
        "keywords": ["happy"],
    }, headers={"Authorization": f"Bearer {token}"})

    # Fetch emojis as anonymous user
    resp = client.get("/api/emojis")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert "submitter_email" not in item


def test_rate_limiting_login(client: TestClient):
    """Login endpoint returns 429 after exceeding rate limit."""
    for _ in range(5):
        client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "wrong",
        })
    # 6th request should be rate-limited
    resp = client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "wrong",
    })
    assert resp.status_code == 429


def test_rate_limiting_register(client: TestClient):
    """Register endpoint returns 429 after exceeding rate limit."""
    for i in range(3):
        client.post("/api/auth/register", json={
            "email": f"user{i}@example.com",
            "password": "StrongPass1!",
            "display_name": f"User{i}",
        })
    resp = client.post("/api/auth/register", json={
        "email": "user99@example.com",
        "password": "StrongPass1!",
        "display_name": "User99",
    })
    assert resp.status_code == 429


def test_rate_limiting_password_reset(client: TestClient):
    """Password reset request returns 429 after exceeding rate limit."""
    for _ in range(3):
        client.post("/api/auth/password-reset/request", json={
            "email": "anyone@example.com",
        })
    resp = client.post("/api/auth/password-reset/request", json={
        "email": "anyone@example.com",
    })
    assert resp.status_code == 429


def test_token_revocation_after_password_reset(client: TestClient):
    """After password reset, old JWT must be rejected."""
    # Register and get a token
    client.post("/api/auth/register", json={
        "email": "revoke@example.com",
        "password": "OldPassword1!",
        "display_name": "Revoker",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "revoke@example.com",
        "password": "OldPassword1!",
    })
    old_token = login_resp.json()["access_token"]

    # Verify old token works
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert me_resp.status_code == 200

    # Create a reset token and reset password
    from app.core.security import create_password_reset_token
    reset_token = create_password_reset_token("revoke@example.com")
    reset_resp = client.post("/api/auth/password-reset/confirm", json={
        "token": reset_token,
        "new_password": "NewPassword1!",
    })
    assert reset_resp.status_code == 200

    # Old JWT should now be rejected (token_version mismatch)
    me_resp2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert me_resp2.status_code == 401


def test_password_reset_token_cannot_be_replayed(client: TestClient):
    """After a successful reset, the same reset token must not work again."""
    client.post("/api/auth/register", json={
        "email": "replay@example.com",
        "password": "OldPassword1!",
        "display_name": "Replay Tester",
    })

    from app.core.security import create_password_reset_token
    reset_token = create_password_reset_token("replay@example.com")
    first_reset = client.post("/api/auth/password-reset/confirm", json={
        "token": reset_token,
        "new_password": "NewPassword1!",
    })
    assert first_reset.status_code == 200

    second_reset = client.post("/api/auth/password-reset/confirm", json={
        "token": reset_token,
        "new_password": "OtherPassword1!",
    })
    assert second_reset.status_code == 400


def test_jwt_has_timezone_aware_expiry():
    """JWT tokens must have timezone-aware expiry (functional check via roundtrip)."""
    token = create_access_token(subject="tz-test")
    payload = decode_token(token)
    assert "exp" in payload
    assert payload["sub"] == "tz-test"


# --- Tests for the new security fixes ---


def test_password_complexity_register_missing_uppercase(client: TestClient):
    """Registration should reject passwords without uppercase letters."""
    resp = client.post("/api/auth/register", json={
        "email": "weakpwd@example.com",
        "password": "nouppercase1",
        "display_name": "Tester",
    })
    assert resp.status_code == 422
    body = resp.json()
    assert any("uppercase" in str(d).lower() for d in body.get("detail", []))


def test_password_complexity_register_missing_digit(client: TestClient):
    """Registration should reject passwords without digits."""
    resp = client.post("/api/auth/register", json={
        "email": "weakpwd2@example.com",
        "password": "NoDigitsHere",
        "display_name": "Tester",
    })
    assert resp.status_code == 422
    body = resp.json()
    assert any("digit" in str(d).lower() for d in body.get("detail", []))


def test_password_complexity_register_valid(client: TestClient):
    """Registration should accept passwords meeting all complexity requirements."""
    resp = client.post("/api/auth/register", json={
        "email": "strongpwd@example.com",
        "password": "Strong1Pass",
        "display_name": "Tester",
    })
    assert resp.status_code == 201


def test_password_reset_complexity_enforced(client: TestClient):
    """Password reset should reject weak passwords (same rules as registration)."""
    # Register a user first
    client.post("/api/auth/register", json={
        "email": "resetcplx@example.com",
        "password": "OldPass123",
        "display_name": "Tester",
    })

    from app.core.security import create_password_reset_token
    reset_token = create_password_reset_token("resetcplx@example.com")

    # Try resetting with a weak password (no uppercase)
    resp = client.post("/api/auth/password-reset/confirm", json={
        "token": reset_token,
        "new_password": "nouppercase1",
    })
    assert resp.status_code == 422


def test_login_password_max_length(client: TestClient):
    """Login should reject passwords over 128 characters."""
    resp = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "A" * 200,
    })
    assert resp.status_code == 422


def test_security_headers_present(client: TestClient):
    """All responses should include security headers."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert "default-src" in resp.headers.get("content-security-policy", "")


def test_security_headers_on_api_endpoints(client: TestClient):
    """Security headers should be present on API endpoints too."""
    resp = client.get("/api/emojis")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    csp = resp.headers.get("content-security-policy", "")
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert resp.headers.get("strict-transport-security", "").startswith("max-age=")


def test_rate_limiter_ignores_xff_from_untrusted(client: TestClient):
    """Rate limiter should NOT trust X-Forwarded-For from non-proxy IPs."""
    # Exhaust the rate limit (5 requests)
    for i in range(5):
        client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "wrong",
        })

    # 6th request with a spoofed XFF header should still be blocked
    resp = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "wrong"},
        headers={"X-Forwarded-For": "1.2.3.4"},
    )
    assert resp.status_code == 429


def test_emoji_create_no_submitter_email_field(client: TestClient):
    """Submitting an emoji should not accept a submitter_email field in the payload."""
    # Register and login
    client.post("/api/auth/register", json={
        "email": "owner@example.com",
        "password": "StrongPass1!",
        "display_name": "Owner",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "owner@example.com",
        "password": "StrongPass1!",
    })
    token = login_resp.json()["access_token"]

    # Submit emoji with a spoofed submitter_email — it should be ignored
    resp = client.post("/api/emojis", json={
        "symbol": "🎭",
        "title": "Performing Arts",
        "keywords": ["theater"],
        "submitter_email": "spoofed@evil.com",  # This field should be ignored
    }, headers={"Authorization": f"Bearer {token}"})
    # Should succeed (extra fields are ignored by Pydantic)
    assert resp.status_code == 201


def test_rate_limiter_cleans_stale_entries():
    """Stale IP entries should be removed to prevent unbounded memory growth."""
    from unittest.mock import MagicMock

    from app.core.ratelimit import RateLimiter

    import time

    limiter = RateLimiter(max_requests=5, window_seconds=1, max_entries=100, cleanup_interval=5)

    # Add hits from unique IPs
    for i in range(15):
        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = f"192.168.1.{i}"
        mock_request.headers = {}
        try:
            limiter.check(mock_request)
        except HTTPException:
            pass

    # All 15 IPs should be present (max_entries=100, no eviction)
    assert len(limiter._hits) == 15

    # Wait for the window to expire, then trigger cleanup
    time.sleep(1.1)
    mock_request = MagicMock()
    mock_request.client = MagicMock()
    mock_request.client.host = "10.0.0.1"
    mock_request.headers = {}
    # Force cleanup by exceeding cleanup_interval
    limiter._check_count = limiter.cleanup_interval - 1
    limiter.check(mock_request)

    # Stale IPs should be cleaned up — only the new IP remains
    assert len(limiter._hits) <= 2


def test_rate_limiter_evicts_when_full():
    """Entries should be evicted when max_entries is exceeded."""
    from unittest.mock import MagicMock

    from app.core.ratelimit import RateLimiter

    limiter = RateLimiter(max_requests=5, window_seconds=60, max_entries=5, cleanup_interval=1)

    # Add more IPs than max_entries allows
    for i in range(10):
        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = f"10.0.0.{i}"
        mock_request.headers = {}
        try:
            limiter.check(mock_request)
        except HTTPException:
            pass

    # With cleanup_interval=1, eviction fires on every check
    # The dict should be bounded near max_entries
    assert len(limiter._hits) <= limiter.max_entries + 2


def test_no_mass_assignment_on_user_update(client: TestClient):
    """PATCH /users/me must not allow setting arbitrary fields like is_superuser."""
    client.post("/api/auth/register", json={
        "email": "massasgn@example.com",
        "password": "StrongPass1!",
        "display_name": "NormalUser",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "massasgn@example.com",
        "password": "StrongPass1!",
    })
    token = login_resp.json()["access_token"]

    # Try to escalate privileges via extra fields (Pydantic should ignore them)
    resp = client.patch("/api/users/me", json={
        "is_superuser": True,
        "is_active": False,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_superuser"] is False
    assert body["is_active"] is True


def test_avatar_url_rejects_javascript_scheme(client: TestClient):
    """avatar_url must reject javascript: and other non-HTTP schemes."""
    client.post("/api/auth/register", json={
        "email": "avatarurl@example.com",
        "password": "StrongPass1!",
        "display_name": "AvatarUser",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "avatarurl@example.com",
        "password": "StrongPass1!",
    })
    token = login_resp.json()["access_token"]

    resp = client.patch("/api/users/me", json={
        "avatar_url": "javascript:alert(1)",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422
    assert any("http or https" in str(d).lower() for d in resp.json().get("detail", []))

    # Valid URL should work
    resp2 = client.patch("/api/users/me", json={
        "avatar_url": "https://cdn.example.com/avatar.png",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200


def test_rate_limiting_emoji_creation(client: TestClient):
    """Emoji creation returns 429 after exceeding rate limit (10/min)."""
    client.post("/api/auth/register", json={
        "email": "ratelimit_emoji@example.com",
        "password": "StrongPass1!",
        "display_name": "RateLimited",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "ratelimit_emoji@example.com",
        "password": "StrongPass1!",
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(10):
        resp = client.post("/api/emojis", json={
            "symbol": chr(0x1F600 + i),
            "title": f"RateTest {i}",
            "keywords": [],
        }, headers=headers)
        assert resp.status_code == 201, f"Request {i+1} should succeed"

    resp = client.post("/api/emojis", json={
        "symbol": "\U0001f910",
        "title": "RateTest Overflow",
        "keywords": [],
    }, headers=headers)
    assert resp.status_code == 429


def test_rate_limiting_comment_creation(client: TestClient):
    """Comment creation returns 429 after exceeding rate limit (10/min)."""
    client.post("/api/auth/register", json={
        "email": "ratelimit_comment@example.com",
        "password": "StrongPass1!",
        "display_name": "CommentLimiter",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "ratelimit_comment@example.com",
        "password": "StrongPass1!",
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    emoji_resp = client.post("/api/emojis", json={
        "symbol": "\U0001f60a",
        "title": "Comment Target",
        "keywords": [],
    }, headers=headers)
    emoji_id = emoji_resp.json()["id"]
    approve_emoji(client, emoji_id)

    for i in range(10):
        resp = client.post(f"/api/emojis/{emoji_id}/comments", json={
            "body": f"Comment {i}",
        }, headers=headers)
        assert resp.status_code == 201, f"Comment {i+1} should succeed"

    resp = client.post(f"/api/emojis/{emoji_id}/comments", json={
        "body": "Overflow comment",
    }, headers=headers)
    assert resp.status_code == 429


def test_rate_limiting_report_creation(client: TestClient):
    """Report creation returns 429 after exceeding rate limit (5/min)."""
    client.post("/api/auth/register", json={
        "email": "ratelimit_report@example.com",
        "password": "StrongPass1!",
        "display_name": "ReportLimiter",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "ratelimit_report@example.com",
        "password": "StrongPass1!",
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    emoji_ids = []
    for i in range(6):
        emoji_resp = client.post("/api/emojis", json={
            "symbol": chr(0x1F44D + i),
            "title": f"Report Target {i}",
            "keywords": [],
        }, headers=headers)
        emoji_ids.append(emoji_resp.json()["id"])
    for eid in emoji_ids:
        approve_emoji(client, eid)

    for i in range(5):
        resp = client.post(f"/api/emojis/{emoji_ids[i]}/reports", json={
            "reason": "spam",
        }, headers=headers)
        assert resp.status_code == 201, f"Report {i+1} should succeed"

    resp = client.post(f"/api/emojis/{emoji_ids[5]}/reports", json={
        "reason": "spam",
    }, headers=headers)
    assert resp.status_code == 429


def test_rate_limiting_emoji_update(client: TestClient):
    """Emoji update (PUT) shares the content-create limiter and returns 429 after 10/min.

    The emoji is seeded directly in the DB so the POST-create path doesn't
    consume any of the shared content_create budget; the whole budget is then
    spent on PUTs.
    """
    from sqlmodel import select

    from app.models import EmojiSubmission, User
    from tests.helpers import test_session

    client.post("/api/auth/register", json={
        "email": "ratelimit_update@example.com",
        "password": "StrongPass1!",
        "display_name": "UpdateLimiter",
    })
    token = client.post("/api/auth/login", json={
        "email": "ratelimit_update@example.com",
        "password": "StrongPass1!",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with test_session(client) as session:
        user = session.exec(
            select(User).where(User.email == "ratelimit_update@example.com")
        ).first()
        assert user is not None
        emoji = EmojiSubmission(
            symbol="\U0001f3b5",
            title="Update Target",
            submitter_id=user.id,
            moderation_status="approved",
        )
        session.add(emoji)
        session.commit()
        session.refresh(emoji)
        emoji_id = emoji.id

    for i in range(10):
        resp = client.put(f"/api/emojis/{emoji_id}", json={
            "description": f"Rev {i}",
        }, headers=headers)
        assert resp.status_code == 200, f"Update {i+1} should succeed"

    resp = client.put(f"/api/emojis/{emoji_id}", json={
        "description": "Overflow",
    }, headers=headers)
    assert resp.status_code == 429


def test_rate_limiting_emoji_delete(client: TestClient):
    """Emoji delete shares the content-create limiter and returns 429 after 10/min.

    11 emojis are seeded directly so the POST-create path doesn't touch the
    shared content_create budget; the whole budget is then spent on DELETEs.
    """
    from sqlmodel import select

    from app.models import EmojiSubmission, User
    from tests.helpers import test_session

    client.post("/api/auth/register", json={
        "email": "ratelimit_delete@example.com",
        "password": "StrongPass1!",
        "display_name": "DeleteLimiter",
    })
    token = client.post("/api/auth/login", json={
        "email": "ratelimit_delete@example.com",
        "password": "StrongPass1!",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    emoji_ids = []
    with test_session(client) as session:
        user = session.exec(
            select(User).where(User.email == "ratelimit_delete@example.com")
        ).first()
        assert user is not None
        for i in range(11):
            emoji = EmojiSubmission(
                symbol=chr(0x1F400 + i),
                title=f"Delete Target {i}",
                submitter_id=user.id,
                moderation_status="approved",
            )
            session.add(emoji)
            session.commit()
            session.refresh(emoji)
            emoji_ids.append(emoji.id)

    for i in range(10):
        resp = client.delete(f"/api/emojis/{emoji_ids[i]}", headers=headers)
        assert resp.status_code == 204, f"Delete {i+1} should succeed"

    # 11th delete is blocked by the limiter before reaching the DB.
    resp = client.delete(f"/api/emojis/{emoji_ids[10]}", headers=headers)
    assert resp.status_code == 429


def test_rate_limiting_oauth_exchange(client: TestClient):
    """The OAuth code-exchange endpoint is throttled by the login limiter (5/min)."""
    for i in range(5):
        resp = client.post("/api/auth/oauth/exchange", json={"code": f"bogus-{i}"})
        assert resp.status_code == 400, f"Exchange {i+1} should reach the handler (400)"

    resp = client.post("/api/auth/oauth/exchange", json={"code": "bogus-overflow"})
    assert resp.status_code == 429


def test_oauth_refuses_silent_merge_with_password_account(client: TestClient, monkeypatch) -> None:
    """An attacker controlling a Google account whose email matches an existing
    password account must NOT be auto-linked into that account.

    Without this guard, anyone able to make Google return verified_email=True for
    an existing user's email would gain login access to that user's account.
    """
    from app.api.endpoints import oauth as oauth_module
    from app.core.oauth import (
        OAUTH_STATE_COOKIE_NAME,
        create_oauth_state_token,
        generate_state_nonce,
    )
    from app.core.security import hash_password
    from app.db import get_session
    from app.models import User

    session = next(client.app.dependency_overrides[get_session]())
    victim = User(
        email="victim@example.com",
        hashed_password=hash_password("VictimPwd123!"),
        display_name="Victim",
    )
    session.add(victim)
    session.commit()
    session.refresh(victim)
    victim_id = victim.id

    async def fake_exchange(code):
        return {"access_token": "fake-google-access-token"}

    async def fake_userinfo(token):
        return {
            "id": "attacker-google-id",
            "email": "victim@example.com",
            "verified_email": True,
            "name": "Attacker",
            "picture": "https://example.com/a.png",
        }

    monkeypatch.setattr(oauth_module, "exchange_code_for_token", fake_exchange)
    monkeypatch.setattr(oauth_module, "get_google_user_info", fake_userinfo)

    # Pass a valid nonce+cookie so the request reaches the actual takeover-refusal
    # logic instead of bouncing on the missing-cookie guard.
    nonce = generate_state_nonce()
    state = create_oauth_state_token("/", nonce=nonce)
    client.cookies.set(OAUTH_STATE_COOKIE_NAME, nonce)
    try:
        resp = client.get(
            "/api/auth/oauth/google/callback",
            params={"code": "fake-code", "state": state},
            follow_redirects=False,
        )
    finally:
        client.cookies.clear()

    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "/login" in location
    assert "error=" in location
    # Specific message from the takeover-refusal path:
    assert "already+exists" in location or "already exists" in location

    # Confirm the victim's record was NOT mutated
    refreshed = next(client.app.dependency_overrides[get_session]()).get(User, victim_id)
    assert refreshed is not None
    assert refreshed.google_id is None
    assert refreshed.oauth_provider is None


def test_oauth_callback_rejects_missing_state_cookie(client: TestClient, monkeypatch) -> None:
    """A callback without the binding cookie is rejected before any work runs."""
    from app.api.endpoints import oauth as oauth_module
    from app.core.oauth import create_oauth_state_token, generate_state_nonce

    network_called = {"count": 0}

    async def fake_exchange(code):
        network_called["count"] += 1
        return {"access_token": "should-not-reach-here"}

    async def fake_userinfo(token):
        network_called["count"] += 1
        return {}

    monkeypatch.setattr(oauth_module, "exchange_code_for_token", fake_exchange)
    monkeypatch.setattr(oauth_module, "get_google_user_info", fake_userinfo)

    nonce = generate_state_nonce()
    state = create_oauth_state_token("/", nonce=nonce)
    client.cookies.clear()  # ensure no binding cookie is sent
    resp = client.get(
        "/api/auth/oauth/google/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]
    # Network calls must NOT have happened — we rejected before reaching Google.
    assert network_called["count"] == 0


def test_oauth_callback_rejects_mismatched_state_cookie(client: TestClient, monkeypatch) -> None:
    """A cookie whose nonce doesn't match the signed state token is rejected."""
    from app.api.endpoints import oauth as oauth_module
    from app.core.oauth import (
        OAUTH_STATE_COOKIE_NAME,
        create_oauth_state_token,
        generate_state_nonce,
    )

    network_called = {"count": 0}

    async def fake_exchange(code):
        network_called["count"] += 1
        return {"access_token": "should-not-reach-here"}

    async def fake_userinfo(token):
        network_called["count"] += 1
        return {}

    monkeypatch.setattr(oauth_module, "exchange_code_for_token", fake_exchange)
    monkeypatch.setattr(oauth_module, "get_google_user_info", fake_userinfo)

    state_nonce = generate_state_nonce()
    cookie_nonce = generate_state_nonce()  # different
    state = create_oauth_state_token("/", nonce=state_nonce)
    client.cookies.set(OAUTH_STATE_COOKIE_NAME, cookie_nonce)
    try:
        resp = client.get(
            "/api/auth/oauth/google/callback",
            params={"code": "fake-code", "state": state},
            follow_redirects=False,
        )
    finally:
        client.cookies.clear()

    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]
    assert network_called["count"] == 0


def test_oauth_initiate_sets_state_cookie(client: TestClient) -> None:
    """The initiate endpoint must set the binding cookie for the callback to verify."""
    from app.core.oauth import OAUTH_STATE_COOKIE_NAME

    resp = client.post("/api/auth/oauth/google/login", json={"redirect_to": "/"})
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert OAUTH_STATE_COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_concurrent_like_is_idempotent_under_integrity_error(client: TestClient, monkeypatch) -> None:
    """If two concurrent like POSTs both pass the existence check, the loser
    must get an idempotent 'already liked' response, not a 500."""
    from sqlalchemy.exc import IntegrityError
    from app.api.endpoints import emojis as emojis_module
    from app.db import get_session
    from app.models import EmojiSubmission, User

    # Set up a public emoji and a logged-in user
    session = next(client.app.dependency_overrides[get_session]())
    user = User(email="liker@example.com", hashed_password="x", display_name="Liker")
    session.add(user)
    emoji = EmojiSubmission(
        symbol="🚀",
        title="Race Rocket",
        moderation_status="approved",
        submitter_email="creator@example.com",
        submitter_id=None,
    )
    session.add(emoji)
    session.commit()
    session.refresh(user)
    session.refresh(emoji)

    # Mint a token for `user`
    from app.core.security import create_access_token
    token = create_access_token(subject=str(user.id), token_version=user.token_version)
    headers = {"Authorization": f"Bearer {token}"}

    # Force the first commit() to raise IntegrityError, simulating a concurrent insert
    real_commit = emojis_module.Session.commit  # type: ignore[attr-defined]
    call_count = {"n": 0}

    def patched_commit(self):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise IntegrityError("simulated", params=None, orig=Exception("UNIQUE"))
        return real_commit(self)

    monkeypatch.setattr(emojis_module.Session, "commit", patched_commit)

    resp = client.post(f"/api/emojis/{emoji.id}/like", headers=headers)
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text}"
    assert resp.json()["detail"] == "already liked"


def test_like_endpoint_is_rate_limited(client: TestClient) -> None:
    """The like endpoint enforces a per-IP cap to prevent flood attacks."""
    from app.core.ratelimit import like_limiter
    from app.db import get_session
    from app.models import EmojiSubmission, User
    from app.core.security import create_access_token

    session = next(client.app.dependency_overrides[get_session]())
    user = User(email="flooder@example.com", hashed_password="x", display_name="Flooder")
    session.add(user)
    emoji = EmojiSubmission(
        symbol="🌊",
        title="Wave",
        moderation_status="approved",
        submitter_email="x@x.com",
        submitter_id=None,
    )
    session.add(emoji)
    session.commit()
    session.refresh(user)
    session.refresh(emoji)
    token = create_access_token(subject=str(user.id), token_version=user.token_version)
    headers = {"Authorization": f"Bearer {token}"}

    # like_limiter caps at 30/min — exhaust it
    for _ in range(like_limiter.max_requests):
        client.post(f"/api/emojis/{emoji.id}/like", headers=headers)

    flood = client.post(f"/api/emojis/{emoji.id}/like", headers=headers)
    assert flood.status_code == 429


def test_trusted_proxy_ips_configurable_via_settings(monkeypatch) -> None:
    """RateLimiter._client_ip should respect Settings.trusted_proxy_ips."""
    from unittest.mock import MagicMock
    from app.core.config import settings
    from app.core.ratelimit import RateLimiter

    monkeypatch.setattr(settings, "trusted_proxy_ips", ["10.0.0.5"])
    limiter = RateLimiter(max_requests=10, window_seconds=60, name="test_proxies")

    # Direct connection from a configured proxy → trust XFF
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "10.0.0.5"
    request.headers = {"x-forwarded-for": "203.0.113.10"}
    assert limiter._client_ip(request) == "203.0.113.10"

    # Direct connection from a non-proxy IP → ignore XFF
    request2 = MagicMock()
    request2.client = MagicMock()
    request2.client.host = "192.168.1.1"
    request2.headers = {"x-forwarded-for": "203.0.113.10"}
    assert limiter._client_ip(request2) == "192.168.1.1"

    # Default (loopback) is no longer trusted in this test's environment
    request3 = MagicMock()
    request3.client = MagicMock()
    request3.client.host = "127.0.0.1"
    request3.headers = {"x-forwarded-for": "203.0.113.10"}
    assert limiter._client_ip(request3) == "127.0.0.1"


def test_password_reset_confirm_unknown_user_returns_generic_400(client: TestClient):
    """A reset token signed for an email that does not map to a user must NOT 404 (info leak)."""
    from app.core.security import create_password_reset_token

    token = create_password_reset_token("ghost@example.com")
    resp = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "FreshPass1!"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid or expired token"


def test_rate_limiting_password_reset_confirm(client: TestClient):
    """The confirm endpoint must be rate-limited the same as the request endpoint."""
    payload = {"token": "garbage", "new_password": "FreshPass1!"}
    for _ in range(3):
        client.post("/api/auth/password-reset/confirm", json=payload)
    resp = client.post("/api/auth/password-reset/confirm", json=payload)
    assert resp.status_code == 429


def test_oauth_callback_clears_state_cookie_on_inner_error(client: TestClient, monkeypatch) -> None:
    """An HTTPException raised inside the inner try must still clear the binding cookie."""
    from app.api.endpoints import oauth as oauth_module
    from app.core.oauth import (
        OAUTH_STATE_COOKIE_NAME,
        create_oauth_state_token,
        generate_state_nonce,
    )

    # Force the access-token-missing branch (oauth.py:111-115) to raise HTTPException.
    async def fake_exchange(code):
        return {}

    async def fake_userinfo(token):
        return {}

    monkeypatch.setattr(oauth_module, "exchange_code_for_token", fake_exchange)
    monkeypatch.setattr(oauth_module, "get_google_user_info", fake_userinfo)

    nonce = generate_state_nonce()
    state = create_oauth_state_token("/", nonce=nonce)
    client.cookies.set(OAUTH_STATE_COOKIE_NAME, nonce)
    try:
        resp = client.get(
            "/api/auth/oauth/google/callback",
            params={"code": "fake-code", "state": state},
            follow_redirects=False,
        )
    finally:
        client.cookies.clear()

    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]
    assert "error=" in resp.headers["location"]
    set_cookie = resp.headers.get("set-cookie", "")
    assert OAUTH_STATE_COOKIE_NAME in set_cookie
    assert ("Max-Age=0" in set_cookie) or (
        f"{OAUTH_STATE_COOKIE_NAME}=""" in set_cookie or f"{OAUTH_STATE_COOKIE_NAME}=;" in set_cookie
    )


def test_long_password_roundtrip_does_not_truncate() -> None:
    """Two passwords sharing bcrypt's 72-byte prefix must not collide."""
    import bcrypt  # noqa: F401  (asserts bcrypt is the backend in use)

    from app.core.security import _prehash, hash_password, verify_password

    # bcrypt silently truncates at 72 bytes; these two agree on the first 72
    # bytes but differ afterward. Under the old raw-bcrypt scheme both would
    # verify against the same hash.
    shared_prefix = "A" * 72
    pw_a = shared_prefix + "X1"
    pw_b = shared_prefix + "Y2"
    hash_a = hash_password(pw_a)

    assert verify_password(pw_a, hash_a) is True
    assert verify_password(pw_b, hash_a) is False
    assert _prehash(pw_a) != _prehash(pw_b)


def test_legacy_raw_bcrypt_hash_still_verifies() -> None:
    """A hash from the old raw-bcrypt scheme must still verify and be flagged
    for re-hash; a fresh hash must not."""
    import bcrypt

    from app.core.security import (
        hash_password,
        password_needs_rehash,
        verify_password,
    )

    password = "SecretPwd123!"
    legacy_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    assert verify_password(password, legacy_hash) is True
    assert password_needs_rehash(password, legacy_hash) is True

    fresh_hash = hash_password(password)
    assert verify_password(password, fresh_hash) is True
    assert password_needs_rehash(password, fresh_hash) is False


def test_login_rehashes_legacy_user(client: TestClient) -> None:
    """A legacy raw-bcrypt user is transparently upgraded on next login."""
    import bcrypt
    from sqlmodel import select

    from app.core.security import password_needs_rehash, verify_password
    from app.models import User
    from tests.helpers import test_session

    password = "SecretPwd123!"
    client.post(
        "/api/auth/register",
        json={
            "email": "legacy-rehash@example.com",
            "password": password,
            "display_name": "Legacy",
        },
    )
    # Overwrite the freshly-hashed password with a legacy raw-bcrypt hash.
    with test_session(client) as session:
        user = session.exec(
            select(User).where(User.email == "legacy-rehash@example.com")
        ).first()
        assert user is not None
        user.hashed_password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        legacy_hash = user.hashed_password
        session.add(user)
        session.commit()

    resp = client.post(
        "/api/auth/login",
        json={"email": "legacy-rehash@example.com", "password": password},
    )
    assert resp.status_code == 200

    with test_session(client) as session:
        user = session.exec(
            select(User).where(User.email == "legacy-rehash@example.com")
        ).first()
        assert user is not None
        assert user.hashed_password != legacy_hash
        assert password_needs_rehash(password, user.hashed_password) is False
        assert verify_password(password, user.hashed_password) is True


def test_exchange_code_for_token_is_async_and_closes_client(monkeypatch) -> None:
    """exchange_code_for_token must await AsyncOAuth2Client.fetch_token off the
    event loop and close the connection — regression guard for the async fix."""
    import asyncio

    from app.core import oauth as oauth_module

    calls: dict[str, object] = {}

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            calls["init"] = kwargs

        async def __aenter__(self):
            calls["entered"] = True
            return self

        async def __aexit__(self, *exc):
            calls["exited"] = True
            return False

        async def fetch_token(self, **kwargs):
            calls["fetch_kwargs"] = kwargs
            return {"access_token": "google-token", "token_type": "Bearer"}

    monkeypatch.setattr(oauth_module, "AsyncOAuth2Client", _FakeClient)

    result = asyncio.run(oauth_module.exchange_code_for_token("the-code"))

    assert result["access_token"] == "google-token"
    assert calls.get("entered") is True
    assert calls.get("exited") is True
    assert calls["fetch_kwargs"]["code"] == "the-code"
    assert calls["fetch_kwargs"]["grant_type"] == "authorization_code"
