"""Sailing and cabin-price models."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CHAR,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base_types import pg_enum
from app.models.enums import CabinType, CruiseLine


class Sailing(Base):
    __tablename__ = "sailings"
    __table_args__ = (
        UniqueConstraint("external_id", "market", name="uq_sailings_external_id_market"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    cruise_line: Mapped[CruiseLine] = mapped_column(
        pg_enum(CruiseLine, "cruise_line"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    market: Mapped[str] = mapped_column(Text, nullable=False)
    ship_name: Mapped[str] = mapped_column(Text, nullable=False)
    destination_region: Mapped[str] = mapped_column(Text, nullable=False)
    departure_port: Mapped[str] = mapped_column(Text, nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration_nights: Mapped[int] = mapped_column(Integer, nullable=False)
    itinerary_ports: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    ship_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    booking_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    last_scraped_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    cabin_prices: Mapped[list["CabinPrice"]] = relationship(
        back_populates="sailing", cascade="all, delete-orphan"
    )


class CabinPrice(Base):
    __tablename__ = "cabin_prices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sailing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sailings.id", ondelete="CASCADE"),
        nullable=False,
    )
    cabin_type: Mapped[CabinType] = mapped_column(
        pg_enum(CabinType, "cabin_type"), nullable=False
    )
    price_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_local: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency_code: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    cabins_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    sailing: Mapped["Sailing"] = relationship(back_populates="cabin_prices")
