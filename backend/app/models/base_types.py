"""Shared column-type helpers for ORM models."""
from __future__ import annotations

import enum
from typing import Type

from sqlalchemy import Enum as SAEnum


def pg_enum(py_enum: Type[enum.Enum], name: str) -> SAEnum:
    """Map a Python enum onto an existing PostgreSQL enum type.

    ``create_type=False`` keeps Alembic/SQLAlchemy from trying to re-CREATE the
    type (it is owned by cruisealert_schema.sql). ``values_callable`` ensures the
    enum *values* are persisted, not the member names.
    """
    return SAEnum(
        py_enum,
        name=name,
        create_type=False,
        native_enum=True,
        values_callable=lambda e: [m.value for m in e],
    )
