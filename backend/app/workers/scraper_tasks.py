"""Scraper Celery tasks: poll_all_cruise_lines, prune_old_prices.

The delta-check (`should_insert_price`) is the single most important piece of
scraper logic and is unit-tested in isolation. Its pure decision is factored
into `price_or_availability_changed` so it can be tested without a database.
"""
from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.sailing import CabinPrice, Sailing
from app.models.scrape import ScrapeRun
from app.services.rapidapi import (
    CRUISE_LINE_CONFIGS,
    CruisePricingClient,
    NormalizedSailing,
)
from app.services.redis_client import get_redis
from app.workers.celery_app import celery_app

logger = logging.getLogger("cruisealert.scraper")

PRICE_RETENTION_DAYS = 120


# --------------------------------------------------------------------------- #
# Delta check
# --------------------------------------------------------------------------- #
def price_or_availability_changed(
    prev_price_usd: Decimal | None,
    prev_cabins_available: int | None,
    new_price_usd: Decimal,
    new_cabins_available: int | None,
) -> bool:
    """Pure decision: should we record a new price row?

    True when there is no previous row (prev_price is None), or when either the
    price OR the availability differs from the previous row.
    """
    if prev_price_usd is None:
        return True
    if Decimal(prev_price_usd) != Decimal(new_price_usd):
        return True
    return prev_cabins_available != new_cabins_available


async def should_insert_price(
    db: AsyncSession,
    sailing_id: str,
    cabin_type: str,
    new_price_usd: Decimal,
    new_cabins_available: int | None,
) -> bool:
    """Return True if a new cabin_prices row should be inserted.

    False only when the latest row for (sailing_id, cabin_type) has BOTH an
    identical price_usd AND identical cabins_available.
    """
    result = await db.execute(
        text(
            """
            SELECT price_usd, cabins_available
            FROM cabin_prices
            WHERE sailing_id = :sid AND cabin_type = :ct
            ORDER BY recorded_at DESC
            LIMIT 1
            """
        ),
        {"sid": str(sailing_id), "ct": cabin_type},
    )
    row = result.first()
    if row is None:
        return True
    return price_or_availability_changed(
        row.price_usd, row.cabins_available, new_price_usd, new_cabins_available
    )


# --------------------------------------------------------------------------- #
# Sailing upsert
# --------------------------------------------------------------------------- #
async def _upsert_sailing(db: AsyncSession, s: NormalizedSailing) -> str:
    """Upsert one sailing on (external_id, market); return its id."""
    stmt = (
        pg_insert(Sailing)
        .values(
            cruise_line=s.cruise_line,
            external_id=s.external_id,
            market=s.market,
            ship_name=s.ship_name,
            destination_region=s.destination_region,
            departure_port=s.departure_port,
            departure_date=s.departure_date,
            return_date=s.return_date,
            duration_nights=s.duration_nights,
            itinerary_ports=s.itinerary_ports,
            ship_image_url=s.ship_image_url,
            booking_url=s.booking_url,
            is_active=True,
            last_scraped_at=datetime.now(timezone.utc),
        )
        .on_conflict_do_update(
            constraint="uq_sailings_external_id_market",
            set_={
                "ship_name": s.ship_name,
                "destination_region": s.destination_region,
                "departure_port": s.departure_port,
                "departure_date": s.departure_date,
                "return_date": s.return_date,
                "duration_nights": s.duration_nights,
                "itinerary_ports": s.itinerary_ports,
                "ship_image_url": s.ship_image_url,
                "booking_url": s.booking_url,
                "is_active": True,
                "last_scraped_at": datetime.now(timezone.utc),
            },
        )
        .returning(Sailing.id)
    )
    result = await db.execute(stmt)
    return str(result.scalar_one())


# --------------------------------------------------------------------------- #
# Core async poll
# --------------------------------------------------------------------------- #
async def _poll_all_cruise_lines() -> dict:
    redis = get_redis()
    summary = {"runs": 0, "sailings_upserted": 0, "prices_inserted": 0, "prices_unchanged": 0}

    async with AsyncSessionLocal() as db:
        # 1. Create an optimistic scrape_runs row per (cruise_line, market).
        run_ids: dict[str, str] = {}
        run_objs: dict[str, ScrapeRun] = {}
        for cruise_line, config in CRUISE_LINE_CONFIGS.items():
            for market in config.markets:
                run = ScrapeRun(cruise_line=cruise_line, market=market, status="success")
                db.add(run)
                await db.flush()
                key = f"{cruise_line}:{market}"
                run_ids[key] = str(run.id)
                run_objs[key] = run
        await db.commit()
        summary["runs"] = len(run_ids)

        # 2. Fetch everything.
        client = CruisePricingClient(settings.RAPIDAPI_KEY, redis)
        try:
            sailings = await client.fetch_all(run_ids)
        finally:
            await client.aclose()

        # Track which (external_id, market) pairs each (line, market) returned,
        # so we can deactivate stale sailings afterward.
        returned_ids_by_combo: dict[str, set[str]] = {k: set() for k in run_ids}

        # 3 + 4. Upsert sailings and run the delta-checked price inserts.
        for s in sailings:
            combo = f"{s.cruise_line}:{s.market}"
            run = run_objs.get(combo)
            try:
                sailing_id = await _upsert_sailing(db, s)
                returned_ids_by_combo.setdefault(combo, set()).add(sailing_id)
                summary["sailings_upserted"] += 1

                for cp in s.cabin_prices:
                    insert = await should_insert_price(
                        db, sailing_id, cp.cabin_type, cp.price_usd, cp.cabins_available
                    )
                    if insert:
                        db.add(
                            CabinPrice(
                                sailing_id=sailing_id,
                                cabin_type=cp.cabin_type,
                                price_usd=cp.price_usd,
                                price_local=cp.price_local,
                                currency_code=cp.currency_code,
                                cabins_available=cp.cabins_available,
                            )
                        )
                        summary["prices_inserted"] += 1
                        if run:
                            run.prices_inserted += 1
                    else:
                        summary["prices_unchanged"] += 1
                        if run:
                            run.prices_unchanged += 1
                if run:
                    run.sailings_found += 1
                await db.commit()
            except Exception:  # noqa: BLE001 - isolate per-sailing failures
                await db.rollback()
                logger.exception("Failed processing sailing %s/%s", s.cruise_line, s.external_id)

        # 5. Deactivate sailings no longer returned for each polled combo.
        for combo, returned in returned_ids_by_combo.items():
            cruise_line, market = combo.split(":", 1)
            run = run_objs.get(combo)
            returned_list = list(returned)
            result = await db.execute(
                text(
                    """
                    UPDATE sailings
                    SET is_active = FALSE
                    WHERE cruise_line = :cl
                      AND market = :mk
                      AND is_active = TRUE
                      AND (:has_returned = FALSE OR NOT (id = ANY(:ids)))
                    """
                ),
                {
                    "cl": cruise_line,
                    "mk": market,
                    "ids": returned_list,
                    "has_returned": len(returned_list) > 0,
                },
            )
            if run is not None:
                run.sailings_deactivated = result.rowcount or 0

        # 6. Finalize scrape_runs.
        now = datetime.now(timezone.utc)
        for run in run_objs.values():
            run.completed_at = now
        await db.commit()

    logger.info("poll_all_cruise_lines summary: %s", summary)
    return summary


# --------------------------------------------------------------------------- #
# Celery task wrappers
# --------------------------------------------------------------------------- #
@celery_app.task(name="app.workers.scraper_tasks.poll_all_cruise_lines")
def poll_all_cruise_lines() -> dict:
    """Poll every cruise line + market, upsert sailings, delta-insert prices."""
    try:
        return asyncio.run(_poll_all_cruise_lines())
    except Exception as exc:  # noqa: BLE001
        logger.exception("poll_all_cruise_lines failed")
        asyncio.run(_record_global_failure(str(exc), traceback.format_exc()))
        raise


async def _record_global_failure(message: str, tb: str) -> None:
    """Best-effort: stamp any still-open runs from this cycle as failed."""
    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                """
                UPDATE scrape_runs
                SET status = 'failed', error_message = :msg, error_traceback = :tb,
                    completed_at = now()
                WHERE completed_at IS NULL
                """
            ),
            {"msg": message[:500], "tb": tb[:8000]},
        )
        await db.commit()


async def _prune_old_prices() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                """
                DELETE FROM cabin_prices
                WHERE recorded_at < (now() - make_interval(days => :days))
                """
            ),
            {"days": PRICE_RETENTION_DAYS},
        )
        await db.commit()
        return result.rowcount or 0


@celery_app.task(name="app.workers.scraper_tasks.prune_old_prices")
def prune_old_prices() -> int:
    """Delete cabin_prices rows older than the retention window."""
    deleted = asyncio.run(_prune_old_prices())
    logger.info("prune_old_prices deleted %d rows", deleted)
    return deleted
