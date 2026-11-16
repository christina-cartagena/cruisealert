"""initial schema

Applies the canonical cruisealert_schema.sql (enums, tables, indexes,
functions, triggers, views) verbatim. The SQL is idempotent (IF NOT EXISTS /
CREATE OR REPLACE / guarded enum creation), so it can run after a manual
``psql -f cruisealert_schema.sql`` with zero drift, or stand alone.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-30
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# backend/cruisealert_schema.sql — alembic/versions/ -> ../../
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "cruisealert_schema.sql"

_DROP_SQL = """
DROP VIEW IF EXISTS active_alerts_with_context CASCADE;
DROP VIEW IF EXISTS cabin_price_trends CASCADE;
DROP VIEW IF EXISTS latest_cabin_prices CASCADE;
DROP FUNCTION IF EXISTS expire_past_alerts() CASCADE;
DROP FUNCTION IF EXISTS enforce_alert_limit() CASCADE;
DROP FUNCTION IF EXISTS provision_user_defaults() CASCADE;
DROP FUNCTION IF EXISTS set_updated_at() CASCADE;
DROP TABLE IF EXISTS alert_events CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS cabin_prices CASCADE;
DROP TABLE IF EXISTS sailings CASCADE;
DROP TABLE IF EXISTS scrape_runs CASCADE;
DROP TABLE IF EXISTS user_poll_schedule CASCADE;
DROP TABLE IF EXISTS notification_preferences CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TYPE IF EXISTS notification_channel CASCADE;
DROP TYPE IF EXISTS scrape_status CASCADE;
DROP TYPE IF EXISTS user_tier CASCADE;
DROP TYPE IF EXISTS alert_status CASCADE;
DROP TYPE IF EXISTS trigger_type CASCADE;
DROP TYPE IF EXISTS cabin_type CASCADE;
DROP TYPE IF EXISTS cruise_line CASCADE;
"""


def upgrade() -> None:
    sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    op.execute(sql)


def downgrade() -> None:
    op.execute(_DROP_SQL)
