"""Apply the schema + seed demo data to a remote Postgres (e.g. Neon).

Uses a raw asyncpg connection so the multi-statement schema SQL runs in one shot
and SSL is handled directly. Reads the plain connection string from $NEON_DSN.

Usage:
    NEON_DSN="postgresql://user:pass@host/db" JWT_SECRET=x python provision_neon.py
"""
import asyncio
import os
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import asyncpg

from seed_demo import SAILINGS

SCHEMA = (Path(__file__).parent / "cruisealert_schema.sql").read_text(encoding="utf-8")


async def main():
    dsn = os.environ["NEON_DSN"].split("?")[0]  # drop libpq query params
    conn = await asyncpg.connect(dsn, ssl=True, statement_cache_size=0)
    try:
        print("Applying schema...")
        await conn.execute(SCHEMA)

        print("Seeding demo data...")
        await conn.execute("DELETE FROM cabin_prices")
        await conn.execute("DELETE FROM sailings")

        n_s = n_p = 0
        for i, (line, ship, region, port, nights, img, cabins) in enumerate(SAILINGS):
            dep = date.today() + timedelta(days=21 + i * 9)
            sid = await conn.fetchval(
                """
                INSERT INTO sailings (cruise_line, external_id, market, ship_name,
                    destination_region, departure_port, departure_date, return_date,
                    duration_nights, itinerary_ports, ship_image_url, booking_url)
                VALUES ($1,$2,'US',$3,$4,$5,$6,$7,$8,$9,$10,$11)
                RETURNING id
                """,
                line, f"{line[:3].upper()}-{uuid.uuid4().hex[:8]}", ship, region, port,
                dep, dep + timedelta(days=nights), nights,
                [port, region + " Port", "Private Island"], img, "https://example.com/book",
            )
            n_s += 1
            for cabin, price_now, price_prev, avail in cabins:
                if price_prev is not None:
                    await conn.execute(
                        "INSERT INTO cabin_prices (sailing_id, cabin_type, price_usd, "
                        "cabins_available, recorded_at) VALUES ($1,$2,$3,$4, now() - interval '2 days')",
                        sid, cabin, Decimal(price_prev), avail,
                    )
                    n_p += 1
                await conn.execute(
                    "INSERT INTO cabin_prices (sailing_id, cabin_type, price_usd, "
                    "cabins_available, recorded_at) VALUES ($1,$2,$3,$4, now())",
                    sid, cabin, Decimal(price_now), avail,
                )
                n_p += 1
        print(f"Done: {n_s} sailings, {n_p} price rows.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
