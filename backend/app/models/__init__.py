"""ORM models. Importing this package registers every table on ``Base.metadata``."""
from __future__ import annotations

from app.models.alert import Alert, AlertEvent
from app.models.enums import (
    AlertStatus,
    CabinType,
    CruiseLine,
    NotificationChannel,
    ScrapeStatus,
    TriggerType,
    UserTier,
)
from app.models.sailing import CabinPrice, Sailing
from app.models.scrape import ScrapeRun
from app.models.user import NotificationPreference, User, UserPollSchedule

__all__ = [
    "Alert",
    "AlertEvent",
    "CabinPrice",
    "Sailing",
    "ScrapeRun",
    "User",
    "NotificationPreference",
    "UserPollSchedule",
    "AlertStatus",
    "CabinType",
    "CruiseLine",
    "NotificationChannel",
    "ScrapeStatus",
    "TriggerType",
    "UserTier",
]
