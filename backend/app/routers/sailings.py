"""Sailing search + detail endpoints.

The search endpoint joins ``sailings`` against the ``cabin_price_trends`` view so
that the lowest current price AND its price trend are computed entirely in SQL
(never in Python, per the build spec).
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.enums import CabinType, UserTier
from app.models.user import User
from app.schemas.sailing import (
    CabinPriceOut,
    CabinTypeDetail,
    SailingDetailResponse,
    SailingListItem,
    SailingListResponse,
)

router = APIRouter()


@router.get("", response_model=SailingListResponse)
async def list_sailings(
    db: AsyncSession = Depends(get_db),
    cruise_line: str | None = Query(default=None, description="Comma-separated enum values"),
    destination_region: str | None = None,
    departure_port: str | None = None,
    departure_date_from: date | None = None,
    departure_date_to: date | None = None,
    duration_min: int | None = None,
    duration_max: int | None = None,
    cabin_type: CabinType | None = None,
    max_price_usd: float | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
) -> SailingListResponse:
    """Search active sailings with current lowest price + price trend.

    Trend is derived from ``cabin_price_trends`` (latest vs prior recorded price).
    """
    where: list[str] = ["s.is_active = TRUE"]
    params: dict = {}

    if cruise_line:
        lines = [c.strip() for c in cruise_line.split(",") if c.strip()]
        if lines:
            where.append("s.cruise_line = ANY(:cruise_lines)")
            params["cruise_lines"] = lines
    if destination_region:
        where.append("s.destination_region ILIKE :dest")
        params["dest"] = f"%{destination_region}%"
    if departure_port:
        where.append("s.departure_port = :dep_port")
        params["dep_port"] = departure_port
    if departure_date_from:
        where.append("s.departure_date >= :date_from")
        params["date_from"] = departure_date_from
    if departure_date_to:
        where.append("s.departure_date <= :date_to")
        params["date_to"] = departure_date_to
    if duration_min is not None:
        where.append("s.duration_nights >= :dur_min")
        params["dur_min"] = duration_min
    if duration_max is not None:
        where.append("s.duration_nights <= :dur_max")
        params["dur_max"] = duration_max

    cabin_filter = ""
    if cabin_type is not None:
        cabin_filter = "AND cpt.cabin_type = :cabin_type"
        params["cabin_type"] = cabin_type.value

    where_sql = " AND ".join(where)

    # `lowest`: the cheapest current cabin (optionally restricted to one cabin
    # type) for each sailing, with its server-computed trend.
    base_cte = f"""
        WITH filtered AS (
            SELECT s.* FROM sailings s WHERE {where_sql}
        ),
        lowest AS (
            SELECT DISTINCT ON (cpt.sailing_id)
                cpt.sailing_id, cpt.cabin_type, cpt.price_usd, cpt.price_trend
            FROM cabin_price_trends cpt
            JOIN filtered f ON f.id = cpt.sailing_id
            WHERE TRUE {cabin_filter}
            ORDER BY cpt.sailing_id, cpt.price_usd ASC
        ),
        joined AS (
            SELECT
                f.id, f.cruise_line, f.market, f.ship_name, f.destination_region,
                f.departure_port, f.departure_date, f.return_date,
                f.duration_nights, f.ship_image_url, f.booking_url,
                l.price_usd AS lowest_price_usd,
                l.cabin_type AS lowest_cabin_type,
                COALESCE(l.price_trend, 'stable') AS price_trend
            FROM filtered f
            LEFT JOIN lowest l ON l.sailing_id = f.id
            WHERE (CAST(:max_price AS numeric) IS NULL
                   OR l.price_usd <= CAST(:max_price AS numeric))
              {"AND l.sailing_id IS NOT NULL" if cabin_type is not None else ""}
        )
    """
    params["max_price"] = max_price_usd

    count_row = await db.execute(text(base_cte + " SELECT count(*) FROM joined"), params)
    total = int(count_row.scalar() or 0)

    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    rows = await db.execute(
        text(
            base_cte
            + """
            SELECT * FROM joined
            ORDER BY departure_date ASC, id ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )

    items = [
        SailingListItem(
            id=r.id,
            cruise_line=r.cruise_line,
            market=r.market,
            ship_name=r.ship_name,
            destination_region=r.destination_region,
            departure_port=r.departure_port,
            departure_date=r.departure_date,
            return_date=r.return_date,
            duration_nights=r.duration_nights,
            ship_image_url=r.ship_image_url,
            booking_url=r.booking_url,
            lowest_price_usd=r.lowest_price_usd,
            lowest_cabin_type=r.lowest_cabin_type,
            price_trend=r.price_trend,
        )
        for r in rows.mappings().all()
    ]

    pages = (total + page_size - 1) // page_size if page_size else 0
    return SailingListResponse(
        items=items, total=total, page=page, page_size=page_size, pages=pages
    )


@router.get("/{sailing_id}", response_model=SailingDetailResponse)
async def get_sailing(
    sailing_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SailingDetailResponse:
    """Full sailing detail. Price history window depends on tier (7d free / 90d pro)."""
    sailing = await db.execute(
        text("SELECT * FROM sailings WHERE id = :id"), {"id": sailing_id}
    )
    s = sailing.mappings().first()
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sailing not found.")

    history_days = 90 if current_user.tier == UserTier.pro else 7

    # Current price + trend per cabin type.
    trend_rows = await db.execute(
        text(
            """
            SELECT cabin_type, price_usd, price_local, currency_code,
                   cabins_available, price_trend
            FROM cabin_price_trends
            WHERE sailing_id = :id
            """
        ),
        {"id": sailing_id},
    )
    trends = {r.cabin_type: r for r in trend_rows.all()}

    # Price history per cabin within the tier window.
    history_rows = await db.execute(
        text(
            """
            SELECT cabin_type, price_usd, price_local, currency_code,
                   cabins_available, recorded_at
            FROM cabin_prices
            WHERE sailing_id = :id
              AND recorded_at >= (now() - make_interval(days => :days))
            ORDER BY recorded_at ASC
            """
        ),
        {"id": sailing_id, "days": history_days},
    )

    history_by_cabin: dict[str, list[CabinPriceOut]] = {}
    for r in history_rows.mappings().all():
        history_by_cabin.setdefault(r["cabin_type"], []).append(
            CabinPriceOut.model_validate(dict(r))
        )

    cabins: list[CabinTypeDetail] = []
    cabin_types = set(trends.keys()) | set(history_by_cabin.keys())
    for ct in sorted(cabin_types):
        t = trends.get(ct)
        cabins.append(
            CabinTypeDetail(
                cabin_type=ct,
                current_price_usd=t.price_usd if t else None,
                current_price_local=t.price_local if t else None,
                currency_code=t.currency_code if t else None,
                cabins_available=t.cabins_available if t else None,
                price_trend=t.price_trend if t else "stable",
                history=history_by_cabin.get(ct, []),
            )
        )

    return SailingDetailResponse(
        id=s["id"],
        cruise_line=s["cruise_line"],
        external_id=s["external_id"],
        market=s["market"],
        ship_name=s["ship_name"],
        destination_region=s["destination_region"],
        departure_port=s["departure_port"],
        departure_date=s["departure_date"],
        return_date=s["return_date"],
        duration_nights=s["duration_nights"],
        itinerary_ports=list(s["itinerary_ports"] or []),
        ship_image_url=s["ship_image_url"],
        booking_url=s["booking_url"],
        is_active=s["is_active"],
        cabins=cabins,
        history_days=history_days,
    )
