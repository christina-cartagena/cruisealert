"""Alert CRUD schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AlertStatus, CabinType, CruiseLine, TriggerType


class AlertCreate(BaseModel):
    sailing_id: uuid.UUID
    cabin_type: CabinType
    trigger_type: TriggerType
    threshold_pct: Decimal | None = Field(default=None, gt=0, le=100)
    threshold_count: int | None = Field(default=None, ge=0)
    cooldown_minutes: int = Field(default=1440, ge=0)
    email_enabled: bool = True
    sms_enabled: bool = False

    @model_validator(mode="after")
    def _validate_trigger_fields(self) -> "AlertCreate":
        if self.trigger_type == TriggerType.availability_threshold and self.threshold_count is None:
            raise ValueError("threshold_count is required for availability_threshold alerts")
        return self


class AlertUpdate(BaseModel):
    threshold_pct: Decimal | None = Field(default=None, gt=0, le=100)
    threshold_count: int | None = Field(default=None, ge=0)
    cooldown_minutes: int | None = Field(default=None, ge=0)
    status: AlertStatus | None = None
    email_enabled: bool | None = None
    sms_enabled: bool | None = None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sailing_id: uuid.UUID
    cabin_type: CabinType
    trigger_type: TriggerType
    threshold_pct: Decimal | None
    threshold_count: int | None
    status: AlertStatus
    cooldown_minutes: int
    email_enabled: bool
    sms_enabled: bool
    last_checked_at: datetime | None
    last_fired_at: datetime | None
    created_at: datetime


class AlertWithSailingOut(AlertOut):
    """Alert enriched with sailing context for the Alerts table."""

    ship_name: str | None = None
    cruise_line: CruiseLine | None = None
    destination_region: str | None = None
    departure_date: date | None = None
