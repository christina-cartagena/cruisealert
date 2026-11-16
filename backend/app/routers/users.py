"""Current-user (`/users/me`) endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import NotificationPreference, User, UserPollSchedule
from app.schemas.user import (
    NotificationPreferenceOut,
    NotificationPreferenceUpdate,
    UserMeOut,
)

router = APIRouter()


@router.get("/me", response_model=UserMeOut)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserMeOut:
    """Return the authenticated user with notification prefs + poll interval."""
    prefs = await db.get(NotificationPreference, current_user.id)
    schedule = await db.get(UserPollSchedule, current_user.id)
    return UserMeOut(
        id=current_user.id,
        email=current_user.email,
        tier=current_user.tier,
        is_email_verified=current_user.is_email_verified,
        email_verified=current_user.is_email_verified,
        created_at=current_user.created_at,
        preferences=NotificationPreferenceOut.model_validate(prefs) if prefs else None,
        poll_interval_min=schedule.poll_interval_min if schedule else None,
    )


@router.patch("/me/preferences", response_model=NotificationPreferenceOut)
async def update_preferences(
    body: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceOut:
    """Update email/SMS notification toggles for the current user."""
    prefs = await db.get(NotificationPreference, current_user.id)
    if prefs is None:
        prefs = NotificationPreference(user_id=current_user.id)
        db.add(prefs)

    if body.email_enabled is not None:
        prefs.email_enabled = body.email_enabled
    if body.sms_enabled is not None:
        # SMS can only be enabled once the phone is verified.
        prefs.sms_enabled = body.sms_enabled and prefs.phone_verified

    await db.commit()
    await db.refresh(prefs)
    return NotificationPreferenceOut.model_validate(prefs)
