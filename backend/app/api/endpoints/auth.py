from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jwt.exceptions import PyJWTError
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.email import send_reset_email
from app.core.ratelimit import login_limiter, password_reset_limiter, register_limiter
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.db import get_session
from app.models import User
from app.schemas.auth import (
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    Token,
    UserLoginRequest,
)
from app.schemas.user import UserCreate, UserPublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, request: Request, session: Session = Depends(get_session)) -> UserPublic:
    register_limiter.check(request)
    statement = select(User).where(User.email == user_in.email)
    if session.exec(statement).first() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        display_name=user_in.display_name,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login_user(payload: UserLoginRequest, request: Request, session: Session = Depends(get_session)) -> Token:
    login_limiter.check(request)
    statement = select(User).where(User.email == payload.email)
    user = session.exec(statement).first()

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None:
        raise invalid_credentials

    # OAuth-only accounts have no password — surface as the same generic error
    # so a login attempt cannot enumerate which emails are Google-only vs. password.
    if user.hashed_password is None:
        logger.info("Login attempted for OAuth-only account email=%s", payload.email)
        raise invalid_credentials

    if not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials

    # Progressive re-hash: upgrade legacy raw-bcrypt hashes to the prehashed
    # scheme on successful login. No forced resets; legacy hashes disappear as
    # users log in. TODO(remove after rollout): drop password_needs_rehash and
    # the raw-bcrypt fallback in _classify_password once no legacy hashes remain.
    if password_needs_rehash(payload.password, user.hashed_password):
        user.hashed_password = hash_password(payload.password)
        user.touch()
        session.add(user)
        session.commit()

    access_token = create_access_token(subject=str(user.id), token_version=user.token_version)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserPublic)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserPublic:
    return current_user


@router.post("/password-reset/request", response_model=PasswordResetResponse)
def request_password_reset(
    payload: PasswordResetRequest, request: Request, session: Session = Depends(get_session)
) -> PasswordResetResponse:
    password_reset_limiter.check(request)
    statement = select(User).where(User.email == payload.email)
    user = session.exec(statement).first()

    if user is None:
        return PasswordResetResponse(message="If the email exists, a reset link will be sent")

    # OAuth-only users have no password to reset — return same generic message
    if user.hashed_password is None:
        return PasswordResetResponse(message="If the email exists, a reset link will be sent")

    reset_token = create_password_reset_token(user.email, token_version=user.token_version)

    try:
        send_reset_email(user.email, reset_token)
    except Exception:
        logger.exception("Failed to send reset email")  # Log but don't reveal to client

    return PasswordResetResponse(message="If the email exists, a reset link will be sent")


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
def confirm_password_reset(
    payload: PasswordResetConfirm,
    request: Request,
    session: Session = Depends(get_session),
) -> PasswordResetResponse:
    password_reset_limiter.check(request)

    invalid_token = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token"
    )

    try:
        token_data = decode_token(payload.token)
    except PyJWTError as exc:
        raise invalid_token from exc

    if token_data.get("type") != "password_reset":
        raise invalid_token

    email = token_data.get("sub")
    if email is None:
        raise invalid_token

    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    if user is None:
        raise invalid_token

    if token_data.get("ver", 0) != user.token_version:
        raise invalid_token

    user.hashed_password = hash_password(payload.new_password)
    user.token_version += 1
    user.touch()
    session.add(user)
    session.commit()

    return PasswordResetResponse(message="Password successfully reset")


__all__ = ["router"]
