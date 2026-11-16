"""Alert CRUD endpoints. The free-tier cap is enforced by a DB trigger (P0001)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertUpdate, AlertWithSailingOut

router = APIRouter()

ALERT_LIMIT_BODY = {
    "code": "alert_limit_reached",
    "message": "Free tier limit is 3 active alerts.",
    "upgrade_url": "/billing/upgrade",
}


def _is_alert_cap_error(exc: Exception) -> bool:
    """True if the DBAPI error is our P0001 free-tier-cap RAISE EXCEPTION."""
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    return sqlstate == "P0001"


@router.get("", response_model=list[AlertWithSailingOut])
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AlertWithSailingOut]:
    """List the current user's alerts, enriched with sailing context."""
    rows = await db.execute(
        text(
            """
            SELECT a.*, s.ship_name, s.cruise_line, s.destination_region, s.departure_date
            FROM alerts a
            JOIN sailings s ON s.id = a.sailing_id
            WHERE a.user_id = :uid
            ORDER BY a.created_at DESC
            """
        ),
        {"uid": current_user.id},
    )
    return [AlertWithSailingOut(**dict(r)) for r in rows.mappings().all()]


@router.post("", response_model=AlertWithSailingOut, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertWithSailingOut:
    """Create an alert. Free-tier cap (>3 live alerts) returns HTTP 403."""
    alert = Alert(
        user_id=current_user.id,
        sailing_id=body.sailing_id,
        cabin_type=body.cabin_type,
        trigger_type=body.trigger_type,
        threshold_pct=body.threshold_pct,
        threshold_count=body.threshold_count,
        cooldown_minutes=body.cooldown_minutes,
        email_enabled=body.email_enabled,
        sms_enabled=body.sms_enabled,
    )
    db.add(alert)
    try:
        await db.commit()
    except (DBAPIError, IntegrityError) as exc:
        await db.rollback()
        if _is_alert_cap_error(exc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ALERT_LIMIT_BODY
            ) from exc
        raise
    await db.refresh(alert)

    # Re-fetch with sailing context for the response.
    row = await db.execute(
        text(
            """
            SELECT a.*, s.ship_name, s.cruise_line, s.destination_region, s.departure_date
            FROM alerts a JOIN sailings s ON s.id = a.sailing_id
            WHERE a.id = :id
            """
        ),
        {"id": alert.id},
    )
    return AlertWithSailingOut(**dict(row.mappings().first()))


@router.patch("/{alert_id}", response_model=AlertWithSailingOut)
async def update_alert(
    alert_id: uuid.UUID,
    body: AlertUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertWithSailingOut:
    """Update an alert's threshold, channels, or status."""
    alert = await db.get(Alert, alert_id)
    if alert is None or alert.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    data = body.model_dump(exclude_unset=True)
    for field_name, value in data.items():
        setattr(alert, field_name, value)

    try:
        await db.commit()
    except (DBAPIError, IntegrityError) as exc:
        await db.rollback()
        if _is_alert_cap_error(exc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ALERT_LIMIT_BODY
            ) from exc
        raise
    await db.refresh(alert)

    row = await db.execute(
        text(
            """
            SELECT a.*, s.ship_name, s.cruise_line, s.destination_region, s.departure_date
            FROM alerts a JOIN sailings s ON s.id = a.sailing_id
            WHERE a.id = :id
            """
        ),
        {"id": alert.id},
    )
    return AlertWithSailingOut(**dict(row.mappings().first()))


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Hard-delete an alert."""
    alert = await db.get(Alert, alert_id)
    if alert is None or alert.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    await db.delete(alert)
    await db.commit()
