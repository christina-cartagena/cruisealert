"""Exhaustive unit tests for the pure alert-engine predicates."""
from decimal import Decimal

import pytest

from app.services.alert_engine import (
    should_fire_availability_threshold,
    should_fire_back_in_stock,
    should_fire_price_drop,
)

D = Decimal


class TestShouldFirePriceDrop:
    def test_any_drop_triggers(self):
        assert should_fire_price_drop(D("90"), D("100"), None) is True

    def test_any_drop_unchanged_false(self):
        assert should_fire_price_drop(D("100"), D("100"), None) is False

    def test_any_drop_price_increase_false(self):
        assert should_fire_price_drop(D("100"), D("90"), None) is False

    def test_threshold_10pct_11pct_drop_true(self):
        # 100 -> 89 is an 11% drop
        assert should_fire_price_drop(D("89"), D("100"), D("10")) is True

    def test_threshold_10pct_9pct_drop_false(self):
        # 100 -> 91 is a 9% drop
        assert should_fire_price_drop(D("91"), D("100"), D("10")) is False

    def test_threshold_exact_10pct_true(self):
        # 100 -> 90 is exactly 10%
        assert should_fire_price_drop(D("90"), D("100"), D("10")) is True

    def test_zero_previous_price_false(self):
        assert should_fire_price_drop(D("0"), D("0"), D("10")) is False


class TestShouldFireBackInStock:
    def test_zero_to_five_true(self):
        assert should_fire_back_in_stock(5, 0) is True

    def test_zero_to_one_true(self):
        assert should_fire_back_in_stock(1, 0) is True

    def test_two_to_five_false(self):
        assert should_fire_back_in_stock(5, 2) is False

    def test_prev_none_false(self):
        assert should_fire_back_in_stock(5, None) is False

    def test_current_none_false(self):
        assert should_fire_back_in_stock(None, 0) is False

    def test_zero_to_zero_false(self):
        assert should_fire_back_in_stock(0, 0) is False


class TestShouldFireAvailabilityThreshold:
    def test_below_threshold_true(self):
        assert should_fire_availability_threshold(3, 5) is True

    def test_equal_threshold_true(self):
        assert should_fire_availability_threshold(5, 5) is True

    def test_above_threshold_false(self):
        assert should_fire_availability_threshold(6, 5) is False

    def test_none_false(self):
        assert should_fire_availability_threshold(None, 5) is False
