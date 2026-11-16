"""Celery instance + Beat schedule."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "cruisealert",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.scraper_tasks", "app.workers.alert_tasks"],
)

celery_app.conf.beat_schedule = {
    "poll-all-cruise-lines": {
        "task": "app.workers.scraper_tasks.poll_all_cruise_lines",
        "schedule": crontab(minute="0", hour="*/4"),  # every 4 hours
    },
    "check-alerts": {
        "task": "app.workers.alert_tasks.check_all_alerts",
        "schedule": crontab(minute="*/30"),  # every 30 minutes
    },
    "expire-past-alerts": {
        "task": "app.workers.alert_tasks.expire_past_alerts",
        "schedule": crontab(hour="0", minute="5"),  # daily at 00:05 UTC
    },
    "prune-old-prices": {
        "task": "app.workers.scraper_tasks.prune_old_prices",
        "schedule": crontab(day_of_week="sunday", hour="2", minute="0"),  # weekly
    },
}

celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_expires = 3600
celery_app.conf.timezone = "UTC"
