from typing import Optional

from pydantic import BaseModel, Field


class OAuthLoginInitiate(BaseModel):
    """Request to initiate OAuth login flow."""

    redirect_to: str = Field(default="/", description="Frontend route to redirect after OAuth success")


class OAuthLoginInitiateResponse(BaseModel):
    """Response containing OAuth authorization URL."""

    authorization_url: str = Field(description="Google OAuth authorization URL")


class GoogleUserInfo(BaseModel):
    """User information from Google OAuth2."""

    id: str = Field(description="Google user ID")
    email: str = Field(description="User email address")
    verified_email: bool = Field(description="Whether email is verified by Google")
    name: Optional[str] = Field(default=None, description="Full name")
    given_name: Optional[str] = Field(default=None, description="First name")
    family_name: Optional[str] = Field(default=None, description="Last name")
    picture: Optional[str] = Field(default=None, description="Profile picture URL")


class OAuthExchangeRequest(BaseModel):
    """Request to exchange a one-time OAuth code for a JWT."""

    code: str


__all__ = [
    "OAuthExchangeRequest",
    "OAuthLoginInitiate",
    "OAuthLoginInitiateResponse",
    "GoogleUserInfo",
]
