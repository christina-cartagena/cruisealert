"""User + notification-preference schemas. Never expose hashed_password."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import UserTier


class UserOut(BaseModel):
    """Public user representation — explicitly excludes hashed_password."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    tier: UserTier
    is_email_verified: bool
    created_at: datetime


class NotificationPreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email_enabled: bool
    sms_enabled: bool
    phone_e164: str | None
    phone_verified: bool
    phone_verified_at: datetime | None = None


class NotificationPreferenceUpdate(BaseModel):
    email_enabled: bool | None = None
    sms_enabled: bool | None = None


class UserMeOut(UserOut):
    # `email_verified` mirrors `is_email_verified` for the frontend's AuthUser shape.
    email_verified: bool
    preferences: NotificationPreferenceOut | None = None
    poll_interval_min: int | None = None
