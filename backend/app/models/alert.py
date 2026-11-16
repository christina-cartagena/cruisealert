"""Alert and alert-event models."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base_types import pg_enum
from app.models.enums import (
    AlertStatus,
    CabinType,
    NotificationChannel,
    TriggerType,
)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "trigger_type <> 'availability_threshold' OR threshold_count IS NOT NULL",
            name="ck_alerts_availability_count",
        ),
        CheckConstraint(
            "threshold_pct IS NULL OR (threshold_pct > 0 AND threshold_pct <= 100)",
            name="ck_alerts_threshold_pct_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    sailing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sailings.id", ondelete="CASCADE"), nullable=False
    )
    cabin_type: Mapped[CabinType] = mapped_column(
        pg_enum(CabinType, "cabin_type"), nullable=False
    )
    trigger_type: Mapped[TriggerType] = mapped_column(
        pg_enum(TriggerType, "trigger_type"), nullable=False
    )
    threshold_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    threshold_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[AlertStatus] = mapped_column(
        pg_enum(AlertStatus, "alert_status"),
        nullable=False,
        server_default=text("'active'"),
    )
    cooldown_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1440")
    )
    email_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    sms_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_fired_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    user: Mapped["User"] = relationship(back_populates="alerts")  # noqa: F821
    events: Mapped[list["AlertEvent"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    trigger_type: Mapped[TriggerType] = mapped_column(
        pg_enum(TriggerType, "trigger_type"), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        pg_enum(NotificationChannel, "notification_channel"), nullable=False
    )
    old_price_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    new_price_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    cabins_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    delivered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    alert: Mapped["Alert"] = relationship(back_populates="events")
