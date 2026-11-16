"""Pure alert-trigger predicates.

These functions take scalar inputs and return a bool. They contain no I/O and
are exhaustively unit tested (see tests/test_alert_engine.py). All price math
uses :class:`~decimal.Decimal`.
"""
from __future__ import annotations

from decimal import Decimal


def should_fire_price_drop(
    current_price: Decimal,
    previous_price: Decimal,
    threshold_pct: Decimal | None,
) -> bool:
    """Return True if the price has dropped enough to fire.

    - If ``threshold_pct`` is None: any drop triggers (current < previous).
    - If ``threshold_pct`` is set: triggers only if the percentage drop is
      greater than or equal to the threshold.

      ``(previous - current) / previous * 100 >= threshold_pct``

    Returns False if ``current >= previous`` (price rose or held), or if
    ``previous_price`` is not positive (cannot compute a percentage).
    """
    if current_price >= previous_price:
        return False

    if threshold_pct is None:
        return True

    if previous_price <= 0:
        return False

    drop_pct = (previous_price - current_price) / previous_price * Decimal(100)
    return drop_pct >= threshold_pct


def should_fire_back_in_stock(
    current_available: int | None,
    previous_available: int | None,
) -> bool:
    """Return True only when availability went from exactly 0 to > 0.

    Returns False if either value is None (we lack reliable data).
    """
    if current_available is None or previous_available is None:
        return False
    return previous_available == 0 and current_available > 0


def should_fire_availability_threshold(
    current_available: int | None,
    threshold_count: int,
) -> bool:
    """Return True when remaining availability is at or below the threshold.

    Returns False if ``current_available`` is None (unknown availability).
    """
    if current_available is None:
        return False
    return current_available <= threshold_count
