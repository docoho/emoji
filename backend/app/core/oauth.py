from __future__ import annotations

import secrets
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import settings

# Google OAuth2 endpoints
GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

# `__Host-` prefix is a browser-enforced contract that requires Secure + Path=/
# + no Domain. We can only opt in when running over HTTPS (i.e. production); in
# dev/test the browser would refuse to set a cookie with that prefix.
OAUTH_STATE_COOKIE_NAME_PROD = "__Host-oauth_state_nonce"
OAUTH_STATE_COOKIE_NAME_DEV = "oauth_state_nonce"


def oauth_state_cookie_name() -> str:
    return (
        OAUTH_STATE_COOKIE_NAME_PROD
        if settings.environment == "production"
        else OAUTH_STATE_COOKIE_NAME_DEV
    )


# Module-level alias frozen at import time. FastAPI captures it as a Cookie
# alias on endpoint definition, so it must be a string, not a callable.
OAUTH_STATE_COOKIE_NAME = oauth_state_cookie_name()
OAUTH_STATE_MAX_AGE_SECONDS = 900  # 15 minutes


def get_state_serializer() -> URLSafeTimedSerializer:
    """Get serializer for OAuth state tokens."""
    return URLSafeTimedSerializer(settings.oauth_state_secret)


def generate_state_nonce() -> str:
    """Generate a fresh nonce for binding state to a single browser session."""
    return secrets.token_urlsafe(16)


def create_oauth_state_token(redirect_to: str = "/", nonce: str = "") -> str:
    """Create a secure state token containing the redirect URL and binding nonce."""
    serializer = get_state_serializer()
    return serializer.dumps({"redirect_to": redirect_to, "nonce": nonce})


def verify_oauth_state_token(
    token: str,
    *,
    expected_nonce: Optional[str] = None,
    max_age: int = OAUTH_STATE_MAX_AGE_SECONDS,
) -> Optional[str]:
    """Verify state token signature, expiry, and (optionally) nonce match.

    Returns the redirect URL if valid, or None if the token is bad, expired,
    or — when `expected_nonce` is provided — the embedded nonce doesn't match.
    """
    serializer = get_state_serializer()
    try:
        data = serializer.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if expected_nonce is not None:
        token_nonce = data.get("nonce", "")
        # Constant-time comparison to avoid leaking nonce length / prefix info.
        if not token_nonce or not secrets.compare_digest(token_nonce, expected_nonce):
            return None
    return data.get("redirect_to", "/")


def get_google_authorization_url(state: str) -> str:
    """
    Build Google OAuth2 authorization URL.

    Args:
        state: State token for CSRF protection

    Returns:
        Complete authorization URL
    """
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict[str, Any]:
    """
    Exchange authorization code for access token.

    Args:
        code: Authorization code from Google

    Returns:
        Token response dictionary

    Raises:
        Exception: If token exchange fails
    """
    # AsyncOAuth2Client subclasses httpx.AsyncClient, so the context manager
    # awaits the token round-trip off the event loop and closes the connection.
    async with AsyncOAuth2Client(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    ) as client:
        token = await client.fetch_token(
            url=GOOGLE_TOKEN_ENDPOINT,
            grant_type="authorization_code",
            code=code,
            redirect_uri=settings.google_redirect_uri,
        )

    return token


async def get_google_user_info(access_token: str) -> dict[str, Any]:
    """
    Fetch user information from Google using access token.

    Args:
        access_token: Google OAuth2 access token

    Returns:
        User info dictionary from Google

    Raises:
        Exception: If user info fetch fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


def validate_redirect_url(redirect_to: str) -> str:
    """
    Validate and sanitize redirect URL to prevent open redirects.

    Args:
        redirect_to: Redirect URL to validate

    Returns:
        Sanitized redirect URL

    Notes:
        - Only allows paths starting with /
        - Prevents absolute URLs
        - Falls back to / if invalid
    """
    if not redirect_to or not isinstance(redirect_to, str):
        return "/"

    # Remove whitespace
    redirect_to = redirect_to.strip()

    # Must start with / and not //  (to prevent protocol-relative URLs)
    if not redirect_to.startswith("/") or redirect_to.startswith("//"):
        return "/"

    # Don't allow URLs with protocols
    if "://" in redirect_to:
        return "/"

    return redirect_to


__all__ = [
    "OAUTH_STATE_COOKIE_NAME",
    "OAUTH_STATE_MAX_AGE_SECONDS",
    "create_oauth_state_token",
    "exchange_code_for_token",
    "generate_state_nonce",
    "get_google_authorization_url",
    "get_google_user_info",
    "validate_redirect_url",
    "verify_oauth_state_token",
]
