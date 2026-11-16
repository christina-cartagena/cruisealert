"""Dispatch-agnostic alert evaluation core.

This holds the full Step-7 alert logic with NO Celery/Redis dependency so it can
run either from a Celery worker (passing ``.delay`` dispatchers) or inline from a
serverless Vercel Cron request (passing the async notification functions). The
Celery worker (app/workers/alert_tasks.py) and the cron router both call
``run_alert_check`` — single source of truth.
"""
from __future__ import annotations

import inspect
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.enums import TriggerType
from app.services import alert_engine
from app.services.notifications import build_sms_message

logger = logging.getLogger("cruisealert.alerts")


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def _fmt_money(value: Decimal | None) -> str:
    if value is None:
        return "$0"
    return f"${value:,.0f}"


def _safe_fmt_date(d) -> str:
    """Format a date like 'Jun 15, 2026' portably (%-d isn't valid on Windows)."""
    if d is None:
        return ""
    try:
        return d.strftime("%b %-d, %Y")
    except ValueError:
        return d.strftime("%b %d, %Y").replace(" 0", " ")


def _pct_change(old: Decimal, new: Decimal) -> str:
    if not old:
        return "0.0%"
    return f"{(old - new) / old * Decimal(100):.1f}%"


def _template_id_for(trigger: str) -> str:
    return {
        TriggerType.price_drop.value: settings.SENDGRID_PRICE_DROP_TEMPLATE_ID,
        TriggerType.back_in_stock.value: settings.SENDGRID_BACK_IN_STOCK_TEMPLATE_ID,
        TriggerType.availability_threshold.value: settings.SENDGRID_AVAIL_WARNING_TEMPLATE_ID,
    }.get(trigger, settings.SENDGRID_PRICE_DROP_TEMPLATE_ID)


def _email_template_data(row, prev_price) -> dict:
    old = Decimal(prev_price) if prev_price is not None else None
    new = Decimal(row.current_price_usd) if row.current_price_usd is not None else None
    savings = (old - new) if (old is not None and new is not None) else None
    return {
        "sailing_ship_name": row.ship_name,
        "sailing_destination": row.destination_region,
        "sailing_departure_date": _safe_fmt_date(row.departure_date),
        "cabin_type": str(row.cabin_type).title(),
        "old_price": _fmt_money(old),
        "new_price": _fmt_money(new),
        "savings": _fmt_money(savings),
        "pct_change": _pct_change(old, new) if (old and new) else "0.0%",
        "booking_url": row.booking_url or settings.FRONTEND_URL,
        "manage_alerts_url": f"{settings.FRONTEND_URL}/alerts",
    }


def _json(data: dict) -> str:
    return json.dumps(data, default=str)


# --------------------------------------------------------------------------- #
# DB helpers
# --------------------------------------------------------------------------- #
async def _previous_price(db: AsyncSession, sailing_id, cabin_type):
    result = await db.execute(
        text(
            """
            SELECT price_usd, cabins_available, recorded_at
            FROM cabin_prices
            WHERE sailing_id = :sid AND cabin_type = :ct
            ORDER BY recorded_at DESC
            OFFSET 1 LIMIT 1
            """
        ),
        {"sid": str(sailing_id), "ct": cabin_type},
    )
    return result.first()


async def _in_cooldown(db: AsyncSession, alert_id, cooldown_minutes: int) -> bool:
    result = await db.execute(
        text(
            """
            SELECT 1 FROM alert_events
            WHERE alert_id = :aid
              AND created_at > (now() - make_interval(mins => :mins))
            LIMIT 1
            """
        ),
        {"aid": str(alert_id), "mins": cooldown_minutes},
    )
    return result.first() is not None


def _evaluate(row, prev_price, prev_avail) -> bool:
    trigger = row.trigger_type
    current_price = row.current_price_usd
    current_avail = row.current_cabins_available

    if trigger == TriggerType.price_drop.value:
        if current_price is None or prev_price is None:
            return False
        return alert_engine.should_fire_price_drop(
            Decimal(current_price), Decimal(prev_price), row.threshold_pct
        )
    if trigger == TriggerType.back_in_stock.value:
        return alert_engine.should_fire_back_in_stock(current_avail, prev_avail)
    if trigger == TriggerType.availability_threshold.value:
        if row.threshold_count is None:
            return False
        return alert_engine.should_fire_availability_threshold(
            current_avail, row.threshold_count
        )
    return False


def _channels_for(row) -> list[str]:
    channels: list[str] = []
    if row.alert_email_enabled and (row.pref_email_enabled is not False) and row.user_email:
        channels.append("email")
    if row.alert_sms_enabled and row.pref_sms_enabled and row.phone_verified and row.phone_e164:
        channels.append("sms")
    return channels


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #
async def run_alert_check(send_email, send_sms) -> dict:
    """Evaluate every active alert; fire + dispatch via the given callables.

    ``send_email(to, template_id, data)`` and ``send_sms(to, message)`` may be
    sync (e.g. Celery ``.delay``) or async (the notification coroutines); both
    are handled. Returns a summary dict.
    """
    summary = {"checked": 0, "fired": 0, "skipped_cooldown": 0, "skipped_no_prev": 0}
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT expire_past_alerts()"))
        await db.commit()

        rows = (await db.execute(text("SELECT * FROM active_alerts_with_context"))).all()
        users_to_stamp: set = set()

        for row in rows:
            interval = row.poll_interval_min or 240
            last = row.user_last_checked_at
            if last is not None and (now - last).total_seconds() / 60.0 < interval:
                continue
            users_to_stamp.add(row.user_id)
            summary["checked"] += 1

            prev = await _previous_price(db, row.sailing_id, row.cabin_type)
            if prev is None:
                await db.execute(
                    text("UPDATE alerts SET last_checked_at = now() WHERE id = :id"),
                    {"id": str(row.alert_id)},
                )
                summary["skipped_no_prev"] += 1
                await db.commit()
                continue

            prev_price = prev.price_usd
            prev_avail = prev.cabins_available
            fires = _evaluate(row, prev_price, prev_avail)

            await db.execute(
                text("UPDATE alerts SET last_checked_at = now() WHERE id = :id"),
                {"id": str(row.alert_id)},
            )

            if not fires:
                await db.commit()
                continue

            if await _in_cooldown(db, row.alert_id, row.cooldown_minutes):
                summary["skipped_cooldown"] += 1
                await db.commit()
                continue

            channels = _channels_for(row)
            if not channels:
                await db.commit()
                continue

            for channel in channels:
                await db.execute(
                    text(
                        """
                        INSERT INTO alert_events
                            (alert_id, trigger_type, channel, old_price_usd,
                             new_price_usd, cabins_available, payload, delivered)
                        VALUES (:aid, :trig, :chan, :old, :new, :avail,
                                CAST(:payload AS JSONB), FALSE)
                        """
                    ),
                    {
                        "aid": str(row.alert_id),
                        "trig": row.trigger_type,
                        "chan": channel,
                        "old": prev_price,
                        "new": row.current_price_usd,
                        "avail": row.current_cabins_available,
                        "payload": _json(_email_template_data(row, prev_price)),
                    },
                )

            await db.execute(
                text("UPDATE alerts SET last_fired_at = now(), status = 'fired' WHERE id = :id"),
                {"id": str(row.alert_id)},
            )
            await db.commit()

            for channel in channels:
                if channel == "email":
                    await _maybe_await(
                        send_email(
                            row.user_email,
                            _template_id_for(row.trigger_type),
                            _email_template_data(row, prev_price),
                        )
                    )
                elif channel == "sms":
                    await _maybe_await(
                        send_sms(
                            row.phone_e164,
                            build_sms_message(
                                line=str(row.cruise_line).replace("_", " ").title(),
                                ship=row.ship_name,
                                sail_date=_safe_fmt_date(row.departure_date),
                                cabin=str(row.cabin_type).title(),
                                new_price=_fmt_money(row.current_price_usd).lstrip("$"),
                                old_price=_fmt_money(prev_price).lstrip("$"),
                                short_url=row.booking_url or settings.FRONTEND_URL,
                            ),
                        )
                    )
            summary["fired"] += 1

        for uid in users_to_stamp:
            await db.execute(
                text("UPDATE user_poll_schedule SET last_checked_at = now() WHERE user_id = :uid"),
                {"uid": str(uid)},
            )
        await db.commit()

    logger.info("run_alert_check summary: %s", summary)
    return summary
