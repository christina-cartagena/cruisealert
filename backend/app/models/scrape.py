"""Scrape-run audit model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base_types import pg_enum
from app.models.enums import CruiseLine, ScrapeStatus


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    cruise_line: Mapped[CruiseLine] = mapped_column(
        pg_enum(CruiseLine, "cruise_line"), nullable=False
    )
    market: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ScrapeStatus] = mapped_column(
        pg_enum(ScrapeStatus, "scrape_status"),
        nullable=False,
        server_default=text("'success'"),
    )
    sailings_found: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    prices_inserted: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    prices_unchanged: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    sailings_deactivated: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
