from __future__ import annotations

import httpx

from .config import settings

MAILERSEND_API_URL = "https://api.mailersend.com/v1/email"


def send_reset_email(to_email: str, reset_token: str) -> None:
    """Send a password reset email via MailerSend HTTP API."""
    reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"

    # Use a client with no proxy to avoid local SOCKS/HTTP proxies
    # that block or interfere with outbound API calls.
    with httpx.Client(trust_env=False, timeout=10) as client:
        response = client.post(
            MAILERSEND_API_URL,
            headers={
                "Authorization": f"Bearer {settings.mailersend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": {"email": settings.mail_from},
                "to": [{"email": to_email}],
                "subject": "Password Reset - Emoji Showcase",
                "text": (
                    "You requested a password reset.\n\n"
                    f"Click the link below to reset your password:\n{reset_link}\n\n"
                    "This link expires in 1 hour.\n\n"
                    "If you didn't request this, you can safely ignore this email."
                ),
                "html": (
                    "<p>You requested a password reset.</p>"
                    f'<p><a href="{reset_link}">Click here to reset your password</a></p>'
                    "<p>This link expires in 1 hour.</p>"
                    "<p>If you didn't request this, you can safely ignore this email.</p>"
                ),
            },
        )
        response.raise_for_status()


__all__ = ["send_reset_email"]
