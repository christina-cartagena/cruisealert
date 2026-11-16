"""Alert-evaluation Celery tasks.

The evaluation logic lives in app/services/alert_runner.py (Celery-free) so it
can be shared with the serverless Vercel Cron path. Here we wrap it with Celery
``.delay`` dispatchers for the out-of-band notification tasks.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.services.alert_runner import run_alert_check
from app.services.notifications import send_email_notification, send_sms_notification
from app.workers.celery_app import celery_app

logger = logging.getLogger("cruisealert.alerts")


@celery_app.task(name="app.workers.alert_tasks.check_all_alerts")
def check_all_alerts() -> dict:
    """Evaluate every active alert; dispatch notifications as Celery subtasks."""
    return asyncio.run(
        run_alert_check(
            send_email=lambda to, tid, data: dispatch_email.delay(to, tid, data),
            send_sms=lambda to, msg: dispatch_sms.delay(to, msg),
        )
    )


@celery_app.task(name="app.workers.alert_tasks.expire_past_alerts")
def expire_past_alerts() -> int:
    """Expire alerts whose sailing has departed (delegates to the DB function)."""

    async def _run() -> int:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT expire_past_alerts()"))
            count = int(result.scalar() or 0)
            await db.commit()
            return count

    expired = asyncio.run(_run())
    logger.info("expire_past_alerts expired %d alerts", expired)
    return expired


@celery_app.task(name="app.workers.alert_tasks.dispatch_email", bind=True, max_retries=3)
def dispatch_email(self, to_email: str, template_id: str, template_data: dict) -> bool:
    """Send one alert email (out of band)."""
    ok = asyncio.run(send_email_notification(to_email, template_id, template_data))
    if not ok:
        logger.warning("Email dispatch failed (will not raise)")
    return ok


@celery_app.task(name="app.workers.alert_tasks.dispatch_sms", bind=True, max_retries=3)
def dispatch_sms(self, to_number: str, message: str) -> bool:
    """Send one alert SMS (out of band)."""
    ok = asyncio.run(send_sms_notification(to_number, message))
    if not ok:
        logger.warning("SMS dispatch failed (will not raise)")
    return ok
