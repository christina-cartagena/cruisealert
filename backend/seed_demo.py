"""Seed the database with demo sailings + price history (dev/demo only).

Usage:
    DATABASE_URL=postgresql+asyncpg://cruisealert:cruisealert@localhost:5432/cruisealert \
    JWT_SECRET=x python seed_demo.py
"""
import asyncio
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text

from app.database import AsyncSessionLocal

# (cruise_line, ship, region, port, nights, image, [(cabin, price_now, price_prev_or_None, avail)])
SAILINGS = [
    ("royal_caribbean", "Wonder of the Seas", "Caribbean", "Miami", 7,
     "https://images.unsplash.com/photo-1548574505-5e239809ee19?w=800",
     [("interior", 699, 749, 14), ("oceanview", 899, 899, 8),
      ("balcony", 1299, 1399, 3), ("suite", 2899, 2899, 1)]),
    ("carnival", "Carnival Celebration", "Bahamas", "Miami", 4,
     "https://images.unsplash.com/photo-1599640842225-85d111c60e6b?w=800",
     [("interior", 429, 459, 20), ("balcony", 749, 699, 6)]),
    ("norwegian", "Norwegian Prima", "Mediterranean", "Barcelona", 10,
     "https://images.unsplash.com/photo-1545459720-aac8509eb02c?w=800",
     [("interior", 1099, 1199, 11), ("oceanview", 1349, 1349, 5),
      ("balcony", 1799, 1899, 2)]),
    ("princess", "Discovery Princess", "Alaska", "Seattle", 7,
     "https://images.unsplash.com/photo-1531253450048-8a4f6c8f1a3b?w=800",
     [("interior", 849, 949, 0), ("balcony", 1499, 1599, 4), ("suite", 3499, 3499, 1)]),
    ("celebrity", "Celebrity Beyond", "Caribbean", "Fort Lauderdale", 9,
     "https://images.unsplash.com/photo-1566375638485-8a0e8f1f1f0b?w=800",
     [("oceanview", 1199, 1199, 9), ("balcony", 1699, 1799, 3), ("suite", 3999, 4199, 1)]),
    ("msc", "MSC Seascape", "Caribbean", "Miami", 7,
     "https://images.unsplash.com/photo-1561731216-c3a4d99437d5?w=800",
     [("interior", 599, 649, 18), ("oceanview", 799, 799, 7), ("balcony", 1199, 1099, 5)]),
    ("holland_america", "Koningsdam", "Mexico", "San Diego", 7,
     "https://images.unsplash.com/photo-1599640842225-85d111c60e6b?w=800",
     [("interior", 749, 799, 12), ("balcony", 1299, 1349, 4)]),
    ("disney", "Disney Wish", "Bahamas", "Port Canaveral", 4,
     "https://images.unsplash.com/photo-1548574505-5e239809ee19?w=800",
     [("oceanview", 1899, 1999, 6), ("balcony", 2799, 2799, 2), ("suite", 5999, 6299, 1)]),
    ("virgin_voyages", "Scarlet Lady", "Caribbean", "Miami", 5,
     "https://images.unsplash.com/photo-1545459720-aac8509eb02c?w=800",
     [("interior", 999, 1099, 10), ("oceanview", 1299, 1299, 4), ("suite", 3299, 3499, 1)]),
    ("royal_caribbean", "Icon of the Seas", "Caribbean", "Miami", 7,
     "https://images.unsplash.com/photo-1566375638485-8a0e8f1f1f0b?w=800",
     [("interior", 1099, 1199, 9), ("balcony", 1899, 1999, 3), ("suite", 4599, 4599, 1)]),
]


async def main():
    async with AsyncSessionLocal() as db:
        # Clean slate for demo data.
        await db.execute(text("DELETE FROM cabin_prices"))
        await db.execute(text("DELETE FROM sailings"))
        await db.commit()

        n_sailings = 0
        n_prices = 0
        for i, (line, ship, region, port, nights, img, cabins) in enumerate(SAILINGS):
            dep = date.today() + timedelta(days=21 + i * 9)
            sid = (
                await db.execute(
                    text(
                        """
                        INSERT INTO sailings (cruise_line, external_id, market, ship_name,
                            destination_region, departure_port, departure_date, return_date,
                            duration_nights, itinerary_ports, ship_image_url, booking_url)
                        VALUES (:cl, :eid, 'US', :ship, :region, :port, :dep, :ret, :nights,
                            :ports, :img, :url)
                        RETURNING id
                        """
                    ),
                    {
                        "cl": line, "eid": f"{line[:3].upper()}-{uuid.uuid4().hex[:8]}",
                        "ship": ship, "region": region, "port": port, "dep": dep,
                        "ret": dep + timedelta(days=nights), "nights": nights,
                        "ports": [port, region + " Port", "Private Island"],
                        "img": img, "url": "https://example.com/book",
                    },
                )
            ).scalar_one()
            n_sailings += 1

            for cabin, price_now, price_prev, avail in cabins:
                # Older row first (if a previous price exists) -> trend.
                if price_prev is not None:
                    await db.execute(
                        text(
                            "INSERT INTO cabin_prices (sailing_id, cabin_type, price_usd, "
                            "cabins_available, recorded_at) VALUES (:s,:c,:p,:a, "
                            "now() - interval '2 days')"
                        ),
                        {"s": sid, "c": cabin, "p": Decimal(price_prev), "a": avail},
                    )
                    n_prices += 1
                await db.execute(
                    text(
                        "INSERT INTO cabin_prices (sailing_id, cabin_type, price_usd, "
                        "cabins_available, recorded_at) VALUES (:s,:c,:p,:a, now())"
                    ),
                    {"s": sid, "c": cabin, "p": Decimal(price_now), "a": avail},
                )
                n_prices += 1
        await db.commit()
        print(f"Seeded {n_sailings} sailings, {n_prices} price rows.")


if __name__ == "__main__":
    asyncio.run(main())
