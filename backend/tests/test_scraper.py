"""Tests for the scraper delta-check and normalizers.

`should_insert_price` is exercised against a tiny fake session so it runs
without a live database; the pure `price_or_availability_changed` decision is
also tested directly.
"""
from decimal import Decimal

import pytest

from app.services.rapidapi import (
    NormalizedSailing,
    normalize_royal_caribbean,
)
from app.workers.scraper_tasks import (
    price_or_availability_changed,
    should_insert_price,
)

D = Decimal


# --------------------------------------------------------------------------- #
# Fake async session that returns a canned "latest row" (or None).
# --------------------------------------------------------------------------- #
class _FakeRow:
    def __init__(self, price_usd, cabins_available):
        self.price_usd = price_usd
        self.cabins_available = cabins_available


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _FakeSession:
    def __init__(self, row):
        self._row = row

    async def execute(self, *_args, **_kwargs):
        return _FakeResult(self._row)


class TestPriceOrAvailabilityChanged:
    def test_no_previous_inserts(self):
        assert price_or_availability_changed(None, None, D("100"), 5) is True

    def test_unchanged_skips(self):
        assert price_or_availability_changed(D("100"), 5, D("100"), 5) is False

    def test_price_changed_inserts(self):
        assert price_or_availability_changed(D("100"), 5, D("90"), 5) is True

    def test_availability_changed_inserts(self):
        assert price_or_availability_changed(D("100"), 5, D("100"), 3) is True


class TestShouldInsertPrice:
    async def test_no_previous_row_always_inserts(self):
        db = _FakeSession(None)
        assert await should_insert_price(db, "sid", "interior", D("100"), 5) is True

    async def test_unchanged_skips(self):
        db = _FakeSession(_FakeRow(D("100"), 5))
        assert await should_insert_price(db, "sid", "interior", D("100"), 5) is False

    async def test_price_changed_inserts(self):
        db = _FakeSession(_FakeRow(D("100"), 5))
        assert await should_insert_price(db, "sid", "interior", D("90"), 5) is True

    async def test_availability_changed_inserts(self):
        db = _FakeSession(_FakeRow(D("100"), 5))
        assert await should_insert_price(db, "sid", "interior", D("100"), 3) is True


class TestNormalizer:
    def test_normalizes_well_formed_sailing(self):
        raw = {
            "id": "RC-12345",
            "ship": "Wonder of the Seas",
            "region": "Caribbean",
            "embarkPort": "Miami",
            "sailDate": "2026-06-15",
            "returnDate": "2026-06-22",
            "nights": 7,
            "ports": ["Miami", "Nassau", "CocoCay"],
            "bookingUrl": "https://example.com/book/RC-12345",
            "prices": [
                {"cabinType": "interior", "priceUsd": "699.00", "available": 12},
                {"cabinType": "balcony", "priceUsd": "1299.00", "available": 3},
            ],
        }
        result = normalize_royal_caribbean(raw, "US")
        assert isinstance(result, NormalizedSailing)
        assert result.external_id == "RC-12345"
        assert result.duration_nights == 7
        assert len(result.cabin_prices) == 2
        assert result.cabin_prices[0].cabin_type == "interior"
        assert result.cabin_prices[0].price_usd == D("699.00")

    def test_missing_required_field_skips(self):
        # No id, ship, or sailDate -> returns None, never raises.
        assert normalize_royal_caribbean({"region": "Caribbean"}, "US") is None

    def test_bad_price_row_is_dropped_not_raised(self):
        raw = {
            "id": "RC-1",
            "ship": "Symphony",
            "sailDate": "2026-07-01",
            "nights": 5,
            "prices": [
                {"cabinType": "interior", "priceUsd": "not-a-number"},
                {"cabinType": "suite", "priceUsd": "2500"},
            ],
        }
        result = normalize_royal_caribbean(raw, "US")
        assert result is not None
        # Only the valid suite row survives.
        assert len(result.cabin_prices) == 1
        assert result.cabin_prices[0].cabin_type == "suite"
