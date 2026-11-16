"""Python enums mirroring the PostgreSQL enum types in cruisealert_schema.sql.

Values (not names) are stored in the database, so the string values here MUST
match the SQL enum labels exactly.
"""
from __future__ import annotations

import enum


class CruiseLine(str, enum.Enum):
    royal_caribbean = "royal_caribbean"
    carnival = "carnival"
    norwegian = "norwegian"
    princess = "princess"
    celebrity = "celebrity"
    msc = "msc"
    holland_america = "holland_america"
    disney = "disney"
    virgin_voyages = "virgin_voyages"


class CabinType(str, enum.Enum):
    interior = "interior"
    oceanview = "oceanview"
    balcony = "balcony"
    suite = "suite"


class TriggerType(str, enum.Enum):
    price_drop = "price_drop"
    back_in_stock = "back_in_stock"
    availability_threshold = "availability_threshold"


class AlertStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    fired = "fired"
    expired = "expired"


class UserTier(str, enum.Enum):
    free = "free"
    pro = "pro"


class ScrapeStatus(str, enum.Enum):
    success = "success"
    failed = "failed"


class NotificationChannel(str, enum.Enum):
    email = "email"
    sms = "sms"
