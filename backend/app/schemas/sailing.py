"""Sailing search + detail schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.enums import CabinType, CruiseLine

PriceTrend = Literal["up", "down", "stable"]


class CabinPriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cabin_type: CabinType
    price_usd: Decimal
    price_local: Decimal | None
    currency_code: str
    cabins_available: int | None
    recorded_at: datetime


class SailingListItem(BaseModel):
    """One row in the search results grid."""

    id: uuid.UUID
    cruise_line: CruiseLine
    market: str
    ship_name: str
    destination_region: str
    departure_port: str
    departure_date: date
    return_date: date | None
    duration_nights: int
    ship_image_url: str | None
    booking_url: str | None
    lowest_price_usd: Decimal | None
    lowest_cabin_type: CabinType | None
    price_trend: PriceTrend


class SailingListResponse(BaseModel):
    items: list[SailingListItem]
    total: int
    page: int
    page_size: int
    pages: int


class CabinTypeDetail(BaseModel):
    cabin_type: CabinType
    current_price_usd: Decimal | None
    current_price_local: Decimal | None
    currency_code: str | None
    cabins_available: int | None
    price_trend: PriceTrend
    history: list[CabinPriceOut]


class SailingDetailResponse(BaseModel):
    id: uuid.UUID
    cruise_line: CruiseLine
    external_id: str
    market: str
    ship_name: str
    destination_region: str
    departure_port: str
    departure_date: date
    return_date: date | None
    duration_nights: int
    itinerary_ports: list[str]
    ship_image_url: str | None
    booking_url: str | None
    is_active: bool
    cabins: list[CabinTypeDetail]
    history_days: int  # 7 (free) or 90 (pro)
