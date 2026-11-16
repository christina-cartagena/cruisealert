"""Notification preferences + phone-verification endpoints (Twilio Verify)."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import NotificationPreference, User
from app.schemas.user import NotificationPreferenceOut, NotificationPreferenceUpdate
from app.services.notifications import check_phone_verification, send_phone_verification

logger = logging.getLogger("cruisealert.notifications")

router = APIRouter()

_E164 = re.compile(r"^\+[1-9]\d{6,14}$")


class StartVerificationRequest(BaseModel):
    phone_e164: str

    @field_validator("phone_e164")
    @classmethod
    def _validate_e164(cls, v: str) -> str:
        if not _E164.match(v):
            raise ValueError("phone_e164 must be E.164 format, e.g. +14155552671")
        return v


class CheckVerificationRequest(StartVerificationRequest):
    code: str


class SentResponse(BaseModel):
    sent: bool


class VerifiedResponse(BaseModel):
    verified: bool


async def _get_or_create_prefs(db: AsyncSession, user_id) -> NotificationPreference:
    prefs = await db.get(NotificationPreference, user_id)
    if prefs is None:
        prefs = NotificationPreference(user_id=user_id)
        db.add(prefs)
        await db.flush()
    return prefs


@router.get("/preferences", response_model=NotificationPreferenceOut)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceOut:
    """Return the current user's notification preferences."""
    prefs = await _get_or_create_prefs(db, current_user.id)
    await db.commit()
    return NotificationPreferenceOut.model_validate(prefs)


@router.patch("/preferences", response_model=NotificationPreferenceOut)
async def update_preferences(
    body: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceOut:
    """Update email/SMS notification toggles. SMS requires a verified phone."""
    prefs = await _get_or_create_prefs(db, current_user.id)
    if body.email_enabled is not None:
        prefs.email_enabled = body.email_enabled
    if body.sms_enabled is not None:
        prefs.sms_enabled = body.sms_enabled and prefs.phone_verified
    await db.commit()
    await db.refresh(prefs)
    return NotificationPreferenceOut.model_validate(prefs)


@router.post("/phone/send-verification", response_model=SentResponse)
async def send_phone_verification_code(
    body: StartVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SentResponse:
    """Send a Twilio Verify SMS code to the user's phone."""
    prefs = await _get_or_create_prefs(db, current_user.id)
    prefs.phone_e164 = body.phone_e164
    prefs.phone_verified = False
    prefs.phone_verified_at = None
    await db.commit()

    ok = await send_phone_verification(body.phone_e164)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send verification code.",
        )
    return SentResponse(sent=True)


@router.post("/phone/check-verification", response_model=VerifiedResponse)
async def check_phone_verification_code(
    body: CheckVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VerifiedResponse:
    """Confirm the Twilio Verify code; on success mark the phone verified."""
    approved = await check_phone_verification(body.phone_e164, body.code)
    if not approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code."
        )

    prefs = await _get_or_create_prefs(db, current_user.id)
    prefs.phone_e164 = body.phone_e164
    prefs.phone_verified = True
    prefs.phone_verified_at = datetime.now(timezone.utc)
    prefs.sms_enabled = True
    await db.commit()
    logger.info("Phone verified user_id=%s", current_user.id)
    return VerifiedResponse(verified=True)
