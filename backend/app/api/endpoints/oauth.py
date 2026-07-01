from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.core.config import settings
from app.core.oauth import (
    OAUTH_STATE_COOKIE_NAME,
    OAUTH_STATE_MAX_AGE_SECONDS,
    create_oauth_state_token,
    exchange_code_for_token,
    generate_state_nonce,
    get_google_authorization_url,
    get_google_user_info,
    validate_redirect_url,
    verify_oauth_state_token,
)
from app.core.oauth_codes import oauth_code_store
from app.core.ratelimit import login_limiter
from app.core.security import create_access_token
from app.db import get_session
from app.models import User
from app.schemas.oauth import OAuthExchangeRequest, OAuthLoginInitiate, OAuthLoginInitiateResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


def _state_cookie_path() -> str:
    # `__Host-` prefix mandates Path=/. In dev we keep the narrower path so the
    # cookie isn't sent on unrelated routes.
    return "/" if settings.environment == "production" else "/api/auth/oauth"


def _set_state_cookie(response: Response, nonce: str) -> None:
    is_prod = settings.environment == "production"
    response.set_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        value=nonce,
        max_age=OAUTH_STATE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        path=_state_cookie_path(),
    )


def _clear_state_cookie(response: Response) -> None:
    response.delete_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        path=_state_cookie_path(),
    )


@router.post("/google/login", response_model=OAuthLoginInitiateResponse)
def initiate_google_login(
    payload: OAuthLoginInitiate,
    response: Response,
) -> OAuthLoginInitiateResponse:
    """Initiate Google OAuth2 login flow.

    Generates a per-request nonce, embeds it in the signed state token,
    AND sets it as an HttpOnly cookie so the callback can prove the response
    is coming back to the same browser that started the flow.
    """
    redirect_to = validate_redirect_url(payload.redirect_to)
    nonce = generate_state_nonce()
    state = create_oauth_state_token(redirect_to, nonce=nonce)
    _set_state_cookie(response, nonce)

    authorization_url = get_google_authorization_url(state)
    return OAuthLoginInitiateResponse(authorization_url=authorization_url)


@router.get("/google/callback")
async def google_oauth_callback(
    code: str,
    state: str,
    session: Session = Depends(get_session),
    state_cookie: Optional[str] = Cookie(default=None, alias=OAUTH_STATE_COOKIE_NAME),
) -> RedirectResponse:
    """Handle Google OAuth2 callback.

    Validates state token + cookie binding, exchanges code for token, fetches
    user info, creates/links user account, and redirects to frontend with
    exchange code.
    """
    # Verify state token AND nonce cookie binding. Either-side missing → reject.
    if not state_cookie:
        error_params = urlencode({"error": "Missing OAuth state cookie"})
        resp = RedirectResponse(
            url=f"{settings.frontend_url}/login?{error_params}",
            status_code=status.HTTP_302_FOUND,
        )
        _clear_state_cookie(resp)
        return resp

    redirect_to = verify_oauth_state_token(state, expected_nonce=state_cookie)
    if redirect_to is None:
        error_params = urlencode({"error": "Invalid or expired OAuth state"})
        resp = RedirectResponse(
            url=f"{settings.frontend_url}/login?{error_params}",
            status_code=status.HTTP_302_FOUND,
        )
        _clear_state_cookie(resp)
        return resp

    try:
        # Exchange authorization code for access token
        token_response = await exchange_code_for_token(code)
        access_token = token_response.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token from Google",
            )

        # Fetch user info from Google
        user_info = await get_google_user_info(access_token)

        # Verify email is verified by Google
        if not user_info.get("verified_email", False):
            error_params = urlencode(
                {"error": "Please use a Google account with a verified email address"}
            )
            resp = RedirectResponse(
                url=f"{settings.frontend_url}/login?{error_params}",
                status_code=status.HTTP_302_FOUND,
            )
            _clear_state_cookie(resp)
            return resp

        # Extract user data
        google_id = user_info.get("id")
        email = user_info.get("email")
        name = user_info.get("name")
        picture = user_info.get("picture")

        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incomplete user information from Google",
            )

        # Check if user exists (by email or google_id)
        statement = select(User).where((User.email == email) | (User.google_id == google_id))
        existing_user = session.exec(statement).first()

        if existing_user:
            # Refuse to silently merge a Google identity into a password account
            # the user has not explicitly opted to link. Without this guard, anyone
            # who can pass Google's `verified_email=True` for an existing user's
            # email would gain login access to that account.
            already_linked = existing_user.google_id == google_id
            if (
                existing_user.hashed_password is not None
                and existing_user.google_id is None
                and not already_linked
            ):
                logger.info(
                    "Refusing OAuth auto-link for password account email=%s", email
                )
                error_params = urlencode(
                    {
                        "error": (
                            "An account with this email already exists. "
                            "Please sign in with your password first, then link your Google account."
                        )
                    }
                )
                resp = RedirectResponse(
                    url=f"{settings.frontend_url}/login?{error_params}",
                    status_code=status.HTTP_302_FOUND,
                )
                _clear_state_cookie(resp)
                return resp

            # Update existing user with OAuth data
            existing_user.google_id = google_id
            existing_user.oauth_provider = "google"
            existing_user.email_verified = True
            existing_user.avatar_url = picture

            # Update display name if not set
            if not existing_user.display_name and name:
                existing_user.display_name = name

            existing_user.touch()
            session.add(existing_user)
            session.commit()
            session.refresh(existing_user)
            user = existing_user
        else:
            # Create new user with OAuth data
            user = User(
                email=email,
                google_id=google_id,
                oauth_provider="google",
                email_verified=True,
                avatar_url=picture,
                display_name=name,
                hashed_password=None,  # OAuth-only user, no password
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        # Generate JWT token
        jwt_token = create_access_token(subject=str(user.id), token_version=user.token_version)

        # Store JWT behind a one-time exchange code
        exchange_code = oauth_code_store.create(jwt_token)

        # Redirect to frontend with short-lived code (not the JWT itself)
        code_params = urlencode({"code": exchange_code})
        resp = RedirectResponse(
            url=f"{settings.frontend_url}{redirect_to}?{code_params}",
            status_code=status.HTTP_302_FOUND,
        )
        _clear_state_cookie(resp)
        return resp

    except HTTPException as exc:
        error_params = urlencode(
            {"error": exc.detail or "OAuth authentication failed."}
        )
        resp = RedirectResponse(
            url=f"{settings.frontend_url}/login?{error_params}",
            status_code=status.HTTP_302_FOUND,
        )
        _clear_state_cookie(resp)
        return resp
    except Exception:
        logger.exception("OAuth callback failed")
        error_params = urlencode({"error": "OAuth authentication failed. Please try again."})
        resp = RedirectResponse(
            url=f"{settings.frontend_url}/login?{error_params}",
            status_code=status.HTTP_302_FOUND,
        )
        _clear_state_cookie(resp)
        return resp


@router.post("/exchange")
def exchange_oauth_code(payload: OAuthExchangeRequest, request: Request) -> dict[str, str]:
    """Exchange a one-time OAuth code for a JWT token."""
    login_limiter.check(request)
    jwt_token = oauth_code_store.exchange(payload.code)
    if jwt_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code",
        )
    return {"access_token": jwt_token, "token_type": "bearer"}


__all__ = ["router"]
