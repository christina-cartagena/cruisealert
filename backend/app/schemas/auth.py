"""Auth request/response schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserTier


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthUser(BaseModel):
    """Compact user object returned alongside auth tokens."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    tier: UserTier
    email_verified: bool


class TokenResponse(BaseModel):
    """Access token + user. The refresh token is delivered via httpOnly cookie."""

    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class VerifyEmailResponse(BaseModel):
    ok: bool
    message: str
