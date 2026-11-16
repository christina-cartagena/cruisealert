"""RapidAPI Cruise Pricing client + per-line normalizers.

This is the most safety-critical service in the app. Design rules:

* Every outbound call is gated by a Redis monthly-usage counter so we never
  blow past the RapidAPI plan's hard 100-calls/month limit.
* Network and parse errors NEVER bubble out of ``fetch_line`` — they are logged
  and turned into an empty list so one bad line can't fail the whole run.
* A single malformed sailing is logged and skipped, never raised.

NOTE: The exact RapidAPI endpoint paths and response field names vary by the
live API documentation. The paths and field maps below reflect the documented
``cruise-prices.p.rapidapi.com`` surface; confirm against the current docs and
adjust ``CRUISE_LINE_CONFIGS`` / the per-line field maps if the provider changes
its schema. The normalizers are intentionally defensive so schema drift degrades
gracefully (skipped sailings) rather than crashing a scrape.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx
from pydantic import BaseModel

from app.config import settings
from app.models.enums import CabinType, CruiseLine

logger = logging.getLogger("cruisealert.rapidapi")

# --------------------------------------------------------------------------- #
# Usage gate
# --------------------------------------------------------------------------- #
USAGE_KEY_PREFIX = "rapidapi:usage"


def _current_month_key() -> str:
    now = datetime.now(timezone.utc)
    return f"{USAGE_KEY_PREFIX}:{now:%Y-%m}"


def _seconds_until_month_end() -> int:
    """Seconds from now until the first instant of next month (UTC)."""
    now = datetime.now(timezone.utc)
    if now.month == 12:
        nxt = now.replace(
            year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    else:
        nxt = now.replace(
            month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    return max(int((nxt - now).total_seconds()), 60)


async def check_and_increment_usage(redis_client) -> bool:
    """Reserve one API call against the monthly budget.

    Returns True if the call is allowed (and the counter was incremented),
    False if the monthly cap has already been reached. Key expires at the end
    of the current month so it self-resets.
    """
    key = _current_month_key()
    # INCR is atomic; treat the post-increment value as our reservation number.
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, _seconds_until_month_end())

    if count > settings.RAPIDAPI_MONTHLY_CAP:
        # Roll back our reservation — we are not making the call.
        await redis_client.decr(key)
        return False
    return True


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CruiseLineConfig:
    cruise_line: str
    rapidapi_endpoint: str
    markets: list[str]
    cabin_types: list[str]
    # Maps NormalizedSailing fields -> raw response keys for this line.
    field_map: dict[str, str] = field(default_factory=dict)


_ALL_CABINS = ["interior", "oceanview", "balcony", "suite"]

# Default raw->normalized field mapping shared by most lines.
_DEFAULT_FIELD_MAP: dict[str, str] = {
    "external_id": "id",
    "ship_name": "ship",
    "destination_region": "region",
    "departure_port": "embarkPort",
    "departure_date": "sailDate",
    "return_date": "returnDate",
    "duration_nights": "nights",
    "itinerary_ports": "ports",
    "ship_image_url": "shipImage",
    "booking_url": "bookingUrl",
    "cabin_prices": "prices",
}

CRUISE_LINE_CONFIGS: dict[str, CruiseLineConfig] = {
    CruiseLine.royal_caribbean.value: CruiseLineConfig(
        cruise_line=CruiseLine.royal_caribbean.value,
        rapidapi_endpoint="/v1/royal-caribbean/sailings",
        markets=["US", "UK"],
        cabin_types=_ALL_CABINS,
        field_map=_DEFAULT_FIELD_MAP,
    ),
    CruiseLine.carnival.value: CruiseLineConfig(
        cruise_line=CruiseLine.carnival.value,
        rapidapi_endpoint="/v1/carnival/sailings",
        markets=["US"],
        cabin_types=_ALL_CABINS,
        field_map=_DEFAULT_FIELD_MAP,
    ),
    CruiseLine.norwegian.value: CruiseLineConfig(
        cruise_line=CruiseLine.norwegian.value,
        rapidapi_endpoint="/v1/norwegian/sailings",
        markets=["US", "UK"],
        cabin_types=_ALL_CABINS,
        field_map=_DEFAULT_FIELD_MAP,
    ),
    CruiseLine.princess.value: CruiseLineConfig(
        cruise_line=CruiseLine.princess.value,
        rapidapi_endpoint="/v1/princess/sailings",
        markets=["US", "AU"],
        cabin_types=_ALL_CABINS,
        field_map=_DEFAULT_FIELD_MAP,
    ),
    CruiseLine.celebrity.value: CruiseLineConfig(
        cruise_line=CruiseLine.celebrity.value,
        rapidapi_endpoint="/v1/celebrity/sailings",
        markets=["US"],
        cabin_types=_ALL_CABINS,
        field_map=_DEFAULT_FIELD_MAP,
    ),
    CruiseLine.msc.value: CruiseLineConfig(
        cruise_line=CruiseLine.msc.value,
        rapidapi_endpoint="/v1/msc/sailings",
        markets=["US", "EU"],
        cabin_types=_ALL_CABINS,
        # MSC uses slightly different keys in the documented response.
        field_map={**_DEFAULT_FIELD_MAP, "departure_port": "portOfEmbarkation",
                   "destination_region": "destination"},
    ),
    CruiseLine.holland_america.value: CruiseLineConfig(
        cruise_line=CruiseLine.holland_america.value,
        rapidapi_endpoint="/v1/holland-america/sailings",
        markets=["US"],
        cabin_types=_ALL_CABINS,
        field_map=_DEFAULT_FIELD_MAP,
    ),
    CruiseLine.disney.value: CruiseLineConfig(
        cruise_line=CruiseLine.disney.value,
        rapidapi_endpoint="/v1/disney/sailings",
        markets=["US"],
        cabin_types=_ALL_CABINS,
        field_map=_DEFAULT_FIELD_MAP,
    ),
    CruiseLine.virgin_voyages.value: CruiseLineConfig(
        cruise_line=CruiseLine.virgin_voyages.value,
        rapidapi_endpoint="/v1/virgin-voyages/sailings",
        markets=["US", "UK"],
        cabin_types=["interior", "oceanview", "balcony", "suite"],
        field_map=_DEFAULT_FIELD_MAP,
    ),
}

# RapidAPI cabin-name aliases -> our cabin_type enum values.
_CABIN_ALIASES: dict[str, str] = {
    "interior": CabinType.interior.value,
    "inside": CabinType.interior.value,
    "oceanview": CabinType.oceanview.value,
    "ocean_view": CabinType.oceanview.value,
    "ocean view": CabinType.oceanview.value,
    "outside": CabinType.oceanview.value,
    "balcony": CabinType.balcony.value,
    "verandah": CabinType.balcony.value,
    "veranda": CabinType.balcony.value,
    "suite": CabinType.suite.value,
    "haven": CabinType.suite.value,
}


# --------------------------------------------------------------------------- #
# Normalized models
# --------------------------------------------------------------------------- #
class NormalizedCabinPrice(BaseModel):
    cabin_type: str
    price_usd: Decimal
    price_local: Decimal | None = None
    currency_code: str = "USD"
    cabins_available: int | None = None


class NormalizedSailing(BaseModel):
    cruise_line: str
    external_id: str
    market: str
    ship_name: str
    destination_region: str
    departure_port: str
    departure_date: date
    return_date: date | None = None
    duration_nights: int
    itinerary_ports: list[str] = []
    ship_image_url: str | None = None
    booking_url: str | None = None
    cabin_prices: list[NormalizedCabinPrice] = []


# --------------------------------------------------------------------------- #
# Parse helpers (never raise)
# --------------------------------------------------------------------------- #
def _to_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _to_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(value)[:19], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def _map_cabin_type(raw_name: str | None) -> str | None:
    if not raw_name:
        return None
    return _CABIN_ALIASES.get(str(raw_name).strip().lower())


def _normalize_cabin_prices(raw_prices, market: str) -> list[NormalizedCabinPrice]:
    out: list[NormalizedCabinPrice] = []
    if not isinstance(raw_prices, list):
        return out
    for rp in raw_prices:
        if not isinstance(rp, dict):
            continue
        cabin = _map_cabin_type(
            rp.get("cabinType") or rp.get("cabin_type") or rp.get("category")
        )
        price_usd = _to_decimal(
            rp.get("priceUsd") or rp.get("price_usd") or rp.get("usd") or rp.get("price")
        )
        if cabin is None or price_usd is None:
            # Without a recognized cabin type and a USD price the row is useless.
            continue
        out.append(
            NormalizedCabinPrice(
                cabin_type=cabin,
                price_usd=price_usd,
                price_local=_to_decimal(rp.get("priceLocal") or rp.get("price_local")),
                currency_code=(rp.get("currency") or rp.get("currencyCode") or "USD")[:3].upper(),
                cabins_available=_to_int(
                    rp.get("cabinsAvailable")
                    if rp.get("cabinsAvailable") is not None
                    else rp.get("available")
                ),
            )
        )
    return out


def _base_normalize(
    raw: dict, cruise_line: str, market: str, field_map: dict[str, str]
) -> NormalizedSailing | None:
    """Shared normalizer used by every per-line function."""
    if not isinstance(raw, dict):
        return None

    fm = field_map

    external_id = raw.get(fm["external_id"]) or raw.get("id") or raw.get("sailingId")
    ship_name = raw.get(fm["ship_name"]) or raw.get("shipName")
    departure_date = _to_date(raw.get(fm["departure_date"]) or raw.get("departureDate"))

    # Required fields — skip the sailing if any are missing.
    if not external_id or not ship_name or departure_date is None:
        logger.warning(
            "Skipping %s sailing with missing required field(s) (id=%s)",
            cruise_line,
            external_id,
        )
        return None

    duration = _to_int(raw.get(fm["duration_nights"]) or raw.get("nights")) or 0
    itinerary = raw.get(fm["itinerary_ports"]) or raw.get("ports") or []
    if not isinstance(itinerary, list):
        itinerary = []

    try:
        return NormalizedSailing(
            cruise_line=cruise_line,
            external_id=str(external_id),
            market=market,
            ship_name=str(ship_name),
            destination_region=str(
                raw.get(fm["destination_region"]) or raw.get("region") or "Unknown"
            ),
            departure_port=str(
                raw.get(fm["departure_port"]) or raw.get("embarkPort") or "Unknown"
            ),
            departure_date=departure_date,
            return_date=_to_date(raw.get(fm["return_date"]) or raw.get("returnDate")),
            duration_nights=duration,
            itinerary_ports=[str(p) for p in itinerary],
            ship_image_url=raw.get(fm["ship_image_url"]) or raw.get("shipImage"),
            booking_url=raw.get(fm["booking_url"]) or raw.get("bookingUrl"),
            cabin_prices=_normalize_cabin_prices(
                raw.get(fm["cabin_prices"]) or raw.get("prices"), market
            ),
        )
    except Exception:  # noqa: BLE001 - defensive; one bad sailing must not crash a run
        logger.warning("Failed to normalize %s sailing id=%s", cruise_line, external_id)
        return None


# --------------------------------------------------------------------------- #
# Per-line normalizers (one per cruise line, per the build spec)
# --------------------------------------------------------------------------- #
def _fm(line: CruiseLine) -> dict[str, str]:
    return CRUISE_LINE_CONFIGS[line.value].field_map


def normalize_royal_caribbean(raw: dict, market: str) -> NormalizedSailing | None:
    return _base_normalize(raw, CruiseLine.royal_caribbean.value, market,
                           _fm(CruiseLine.royal_caribbean))


def normalize_carnival(raw: dict, market: str) -> NormalizedSailing | None:
    return _base_normalize(raw, CruiseLine.carnival.value, market, _fm(CruiseLine.carnival))


def normalize_norwegian(raw: dict, market: str) -> NormalizedSailing | None:
    return _base_normalize(raw, CruiseLine.norwegian.value, market, _fm(CruiseLine.norwegian))


def normalize_princess(raw: dict, market: str) -> NormalizedSailing | None:
    return _base_normalize(raw, CruiseLine.princess.value, market, _fm(CruiseLine.princess))


def normalize_celebrity(raw: dict, market: str) -> NormalizedSailing | None:
    return _base_normalize(raw, CruiseLine.celebrity.value, market, _fm(CruiseLine.celebrity))


def normalize_msc(raw: dict, market: str) -> NormalizedSailing | None:
    return _base_normalize(raw, CruiseLine.msc.value, market, _fm(CruiseLine.msc))


def normalize_holland_america(raw: dict, market: str) -> NormalizedSailing | None:
    return _base_normalize(raw, CruiseLine.holland_america.value, market,
                           _fm(CruiseLine.holland_america))


def normalize_disney(raw: dict, market: str) -> NormalizedSailing | None:
    return _base_normalize(raw, CruiseLine.disney.value, market, _fm(CruiseLine.disney))


def normalize_virgin_voyages(raw: dict, market: str) -> NormalizedSailing | None:
    return _base_normalize(raw, CruiseLine.virgin_voyages.value, market,
                           _fm(CruiseLine.virgin_voyages))


NORMALIZERS = {
    CruiseLine.royal_caribbean.value: normalize_royal_caribbean,
    CruiseLine.carnival.value: normalize_carnival,
    CruiseLine.norwegian.value: normalize_norwegian,
    CruiseLine.princess.value: normalize_princess,
    CruiseLine.celebrity.value: normalize_celebrity,
    CruiseLine.msc.value: normalize_msc,
    CruiseLine.holland_america.value: normalize_holland_america,
    CruiseLine.disney.value: normalize_disney,
    CruiseLine.virgin_voyages.value: normalize_virgin_voyages,
}


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
class CruisePricingClient:
    """Thin async client over the RapidAPI Cruise Pricing API."""

    def __init__(self, api_key: str, redis_client):
        self.api_key = api_key
        self.redis = redis_client
        self.http = httpx.AsyncClient(timeout=30.0)
        self._semaphore = asyncio.Semaphore(3)

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": settings.RAPIDAPI_HOST,
            "Accept": "application/json",
        }

    @staticmethod
    def _extract_sailings(payload) -> list[dict]:
        """Tolerate both ``[...]`` and ``{"sailings": [...]}`` response shapes."""
        if isinstance(payload, list):
            return [s for s in payload if isinstance(s, dict)]
        if isinstance(payload, dict):
            for key in ("sailings", "data", "results", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [s for s in value if isinstance(s, dict)]
        return []

    async def fetch_line(
        self, cruise_line: str, market: str, scrape_run_id: str
    ) -> list[NormalizedSailing]:
        """Fetch + normalize all sailings for one (cruise_line, market).

        Checks the usage gate first. On any HTTP/parse error, logs and returns
        an empty list — never raises.
        """
        config = CRUISE_LINE_CONFIGS.get(cruise_line)
        normalizer = NORMALIZERS.get(cruise_line)
        if config is None or normalizer is None:
            logger.error("No config/normalizer for cruise_line=%s", cruise_line)
            return []

        async with self._semaphore:
            allowed = await check_and_increment_usage(self.redis)
            if not allowed:
                logger.warning(
                    "RapidAPI monthly cap reached; skipping %s/%s (run=%s)",
                    cruise_line,
                    market,
                    scrape_run_id,
                )
                return []

            url = f"https://{settings.RAPIDAPI_HOST}{config.rapidapi_endpoint}"
            try:
                resp = await self.http.get(
                    url, headers=self._headers, params={"market": market}
                )
                resp.raise_for_status()
                payload = resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                logger.error(
                    "RapidAPI fetch failed for %s/%s (run=%s): %s",
                    cruise_line,
                    market,
                    scrape_run_id,
                    exc,
                )
                return []

        sailings: list[NormalizedSailing] = []
        for raw in self._extract_sailings(payload):
            normalized = normalizer(raw, market)
            if normalized is not None:
                sailings.append(normalized)
        logger.info(
            "Fetched %d sailings for %s/%s (run=%s)",
            len(sailings),
            cruise_line,
            market,
            scrape_run_id,
        )
        return sailings

    async def fetch_all(
        self, scrape_run_ids: dict[str, str]
    ) -> list[NormalizedSailing]:
        """Fetch every configured (cruise_line, market) concurrently (max 3).

        ``scrape_run_ids`` maps ``"{cruise_line}:{market}"`` -> scrape_run id.
        The internal semaphore caps concurrency at 3 to avoid rate limiting.
        """
        tasks = []
        for cruise_line, config in CRUISE_LINE_CONFIGS.items():
            for market in config.markets:
                run_id = scrape_run_ids.get(f"{cruise_line}:{market}", "")
                tasks.append(self.fetch_line(cruise_line, market, run_id))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_sailings: list[NormalizedSailing] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("fetch_line task raised: %s", result)
                continue
            all_sailings.extend(result)
        return all_sailings

    async def aclose(self) -> None:
        await self.http.aclose()
