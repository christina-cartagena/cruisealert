"""DEMO price feed.

The real price feed is the RapidAPI scraper (app/services/rapidapi.py), but that
needs a live RapidAPI subscription, verified per-line endpoints, AND Redis for
the usage gate — none of which exist on Vercel's serverless runtime. This module
is a stand-in that nudges seeded prices so the alert pipeline is demonstrably
live. It is gated behind ``settings.DEMO_PRICE_FEED`` and is NOT real data.

Replace this with the real scraper (on a worker host with Redis) for production.
"""
from __future__ import annotations

import logging
import random
from decimal import Decimal

from sqlalchemy import text

from app.database import AsyncSessionLocal

logger = logging.getLogger("cruisealert.demo_feed")


async def refresh_demo_prices() -> int:
    """Append a fresh price row per cabin, mostly nudging downward (to trigger
    price-drop alerts). Returns the number of rows inserted."""
    inserted = 0
    async with AsyncSessionLocal() as db:
        latest = (
            await db.execute(
                text(
                    """
                    SELECT DISTINCT ON (cp.sailing_id, cp.cabin_type)
                        cp.sailing_id, cp.cabin_type, cp.price_usd, cp.cabins_available
                    FROM cabin_prices cp
                    JOIN sailings s ON s.id = cp.sailing_id AND s.is_active = TRUE
                    ORDER BY cp.sailing_id, cp.cabin_type, cp.recorded_at DESC
                    """
                )
            )
        ).all()

        for r in latest:
            # Bias downward: ~65% chance of a drop of 1-8%, else a small rise.
            pct = random.uniform(-0.08, 0.02)
            new_price = (Decimal(r.price_usd) * (Decimal(1) + Decimal(str(round(pct, 4))))).quantize(
                Decimal("1.00")
            )
            if new_price <= 0:
                continue
            avail = r.cabins_available
            if avail is not None:
                avail = max(0, avail + random.choice([-2, -1, 0, 0, 1]))
            if new_price == Decimal(r.price_usd) and avail == r.cabins_available:
                continue  # delta-check: nothing changed
            await db.execute(
                text(
                    "INSERT INTO cabin_prices (sailing_id, cabin_type, price_usd, "
                    "cabins_available, recorded_at) VALUES (:s,:c,:p,:a, now())"
                ),
                {"s": str(r.sailing_id), "c": r.cabin_type, "p": new_price, "a": avail},
            )
            inserted += 1
        await db.commit()

    logger.info("refresh_demo_prices inserted %d rows", inserted)
    return inserted
