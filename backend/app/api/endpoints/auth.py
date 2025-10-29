from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    hash_password,
    verify_password,
    verify_password_reset_token,
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

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, session: Session = Depends(get_session)) -> UserPublic:
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
def login_user(payload: UserLoginRequest, session: Session = Depends(get_session)) -> Token:
    statement = select(User).where(User.email == payload.email)
    user = session.exec(statement).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token)


@router.get("/me", response_model=UserPublic)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserPublic:
    return current_user


@router.post("/password-reset/request", response_model=PasswordResetResponse)
def request_password_reset(
    payload: PasswordResetRequest, session: Session = Depends(get_session)
) -> PasswordResetResponse:
    statement = select(User).where(User.email == payload.email)
    user = session.exec(statement).first()
    
    if user is None:
        return PasswordResetResponse(message="If the email exists, a reset link will be sent")
    
    reset_token = create_password_reset_token(user.email)
    
    return PasswordResetResponse(
        message="Password reset token generated (in production, this would be emailed)",
        reset_token=reset_token,
    )


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
def confirm_password_reset(
    payload: PasswordResetConfirm, session: Session = Depends(get_session)
) -> PasswordResetResponse:
    email = verify_password_reset_token(payload.token)
    if email is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.hashed_password = hash_password(payload.new_password)
    user.touch()
    session.add(user)
    session.commit()
    
    return PasswordResetResponse(message="Password successfully reset")


__all__ = ["router"]
