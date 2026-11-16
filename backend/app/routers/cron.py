"""Scheduled-task endpoints, triggered by Vercel Cron.

Vercel Cron invokes these GET endpoints on a schedule and (when CRON_SECRET is
set) sends ``Authorization: Bearer <CRON_SECRET>``. We accept that header or a
``?secret=`` query param (for manual triggering). This replaces the Celery Beat
schedule for the serverless deployment.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.config import settings
from app.services.alert_runner import run_alert_check
from app.services.demo_feed import refresh_demo_prices
from app.services.notifications import send_email_notification, send_sms_notification

logger = logging.getLogger("cruisealert.cron")

router = APIRouter()


def _authorize(authorization: str | None, secret: str | None) -> None:
    expected = settings.CRON_SECRET
    if not expected:
        # No secret configured -> allow (e.g. local dev). Log it.
        logger.warning("CRON_SECRET not set; cron endpoint is unprotected.")
        return
    presented = secret or (
        authorization.split(" ", 1)[1] if authorization and " " in authorization else authorization
    )
    if presented != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad cron secret.")


@router.get("/tick")
async def tick(
    authorization: str | None = Header(default=None),
    secret: str | None = Query(default=None),
) -> dict:
    """One scheduled cycle: refresh prices (demo feed) then evaluate alerts."""
    _authorize(authorization, secret)

    refreshed = 0
    if settings.DEMO_PRICE_FEED:
        refreshed = await refresh_demo_prices()

    alerts = await run_alert_check(
        send_email=send_email_notification,
        send_sms=send_sms_notification,
    )
    return {"prices_refreshed": refreshed, "alerts": alerts, "demo_feed": settings.DEMO_PRICE_FEED}


@router.get("/check-alerts")
async def check_alerts(
    authorization: str | None = Header(default=None),
    secret: str | None = Query(default=None),
) -> dict:
    """Evaluate alerts only (no price refresh)."""
    _authorize(authorization, secret)
    alerts = await run_alert_check(
        send_email=send_email_notification,
        send_sms=send_sms_notification,
    )
    return {"alerts": alerts}
