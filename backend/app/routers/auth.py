"""Authentication endpoints: register, login, refresh, logout, verify-email."""
from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthUser,
    LoginRequest,
    MessageResponse,
    RefreshResponse,
    RegisterRequest,
    TokenResponse,
    VerifyEmailResponse,
)
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.services.notifications import send_email_notification

logger = logging.getLogger("cruisealert.auth")

router = APIRouter()

REFRESH_COOKIE = "refresh_token"


def _auth_user(user: User) -> AuthUser:
    return AuthUser(
        id=user.id,
        email=user.email,
        tier=user.tier,
        email_verified=user.is_email_verified,
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    # In production the frontend and API live on different domains, so the
    # refresh cookie must be SameSite=None; Secure to be sent on cross-site
    # XHR. Locally we use Lax over http.
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=settings.JWT_REFRESH_EXPIRE_DAYS * 24 * 3600,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path="/")


async def _send_verification_email(user: User, token: str) -> None:
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    await send_email_notification(
        to_email=user.email,
        template_id=settings.SENDGRID_VERIFY_EMAIL_TEMPLATE_ID,
        template_data={"verify_url": verify_url},
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Create a user, send a verification email, return access + set refresh cookie."""
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    verification_token = secrets.token_urlsafe(32)
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        email_verification_token=verification_token,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await _send_verification_email(user, verification_token)
    logger.info("Registered user_id=%s", user.id)

    refresh = create_refresh_token(str(user.id))
    _set_refresh_cookie(response, refresh)
    access = create_access_token(str(user.id), user.tier.value)
    return TokenResponse(access_token=access, user=_auth_user(user))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Verify credentials, return an access token, set the refresh cookie."""
    user = await db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    refresh = create_refresh_token(str(user.id))
    _set_refresh_cookie(response, refresh)
    access = create_access_token(str(user.id), user.tier.value)
    logger.info("Login user_id=%s", user.id)
    return TokenResponse(access_token=access, user=_auth_user(user))


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Issue a new access token from a valid refresh cookie."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token."
        )

    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type."
        )

    user_id = payload.get("sub")
    user = await db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found."
        )

    # Rotate the refresh token on every refresh.
    new_refresh = create_refresh_token(str(user.id))
    _set_refresh_cookie(response, new_refresh)
    access = create_access_token(str(user.id), user.tier.value)
    return RefreshResponse(access_token=access)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response) -> MessageResponse:
    """Clear the refresh cookie."""
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out.")


@router.get("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> VerifyEmailResponse:
    """Mark a user's email as verified given a valid verification token."""
    user = await db.scalar(
        select(User).where(User.email_verification_token == token)
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token.",
        )

    user.is_email_verified = True
    user.email_verification_token = None
    await db.commit()
    logger.info("Email verified user_id=%s", user.id)
    return VerifyEmailResponse(ok=True, message="Email verified.")
