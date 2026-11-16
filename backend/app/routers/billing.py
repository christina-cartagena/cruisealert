"""Stripe billing: checkout sessions, portal sessions, and webhook handling."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import stripe as stripe_service

logger = logging.getLogger("cruisealert.billing")

router = APIRouter()


class CheckoutRequest(BaseModel):
    plan: str = "monthly"  # "monthly" | "annual" | a raw price_id


class UrlResponse(BaseModel):
    url: str


@router.post("/create-checkout-session", response_model=UrlResponse)
async def create_checkout_session(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UrlResponse:
    """Create a Stripe Checkout session for a Pro subscription."""
    price_id = stripe_service.resolve_price_id(body.plan)
    if not price_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown plan.")

    try:
        customer_id = stripe_service.get_or_create_customer(
            email=current_user.email,
            user_id=str(current_user.id),
            existing_customer_id=current_user.stripe_customer_id,
        )
        if customer_id != current_user.stripe_customer_id:
            current_user.stripe_customer_id = customer_id
            await db.commit()

        url = stripe_service.create_checkout_session(
            customer_id=customer_id, price_id=price_id, user_id=str(current_user.id)
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Stripe checkout failed user_id=%s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Payment provider error."
        ) from exc
    return UrlResponse(url=url)


@router.post("/portal-session", response_model=UrlResponse)
async def create_portal_session(
    current_user: User = Depends(get_current_user),
) -> UrlResponse:
    """Create a Stripe billing-portal session for the current user."""
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No Stripe customer on file."
        )
    try:
        url = stripe_service.create_portal_session(current_user.stripe_customer_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Stripe portal failed user_id=%s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Payment provider error."
        ) from exc
    return UrlResponse(url=url)


async def _user_by_customer(db: AsyncSession, customer_id: str | None) -> User | None:
    if not customer_id:
        return None
    return await db.scalar(select(User).where(User.stripe_customer_id == customer_id))


async def _activate_pro(db: AsyncSession, user: User, subscription_id: str | None) -> None:
    user.tier = "pro"
    if subscription_id:
        user.stripe_subscription_id = subscription_id
    await db.execute(
        text("UPDATE user_poll_schedule SET poll_interval_min = 30 WHERE user_id = :uid"),
        {"uid": user.id},
    )
    await db.commit()
    logger.info("Upgraded user_id=%s to pro", user.id)


async def _downgrade_free(db: AsyncSession, user: User) -> None:
    user.tier = "free"
    user.stripe_subscription_id = None
    await db.execute(
        text("UPDATE user_poll_schedule SET poll_interval_min = 240 WHERE user_id = :uid"),
        {"uid": user.id},
    )
    # Pause all but the 3 oldest live alerts so the free cap holds.
    await db.execute(
        text(
            """
            UPDATE alerts SET status = 'paused'
            WHERE id IN (
                SELECT id FROM alerts
                WHERE user_id = :uid AND status IN ('active', 'fired')
                ORDER BY created_at ASC
                OFFSET 3
            )
            """
        ),
        {"uid": user.id},
    )
    await db.commit()
    logger.info("Downgraded user_id=%s to free", user.id)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default="", alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle Stripe webhook events (signature-verified)."""
    payload = await request.body()
    try:
        event = stripe_service.verify_webhook(payload, stripe_signature)
    except Exception as exc:  # noqa: BLE001 - invalid signature / payload
        logger.warning("Stripe webhook signature verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature."
        ) from exc

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user = await _user_by_customer(db, obj.get("customer"))
        if user is None and obj.get("client_reference_id"):
            user = await db.get(User, obj["client_reference_id"])
        if user is not None:
            await _activate_pro(db, user, obj.get("subscription"))

    elif event_type == "customer.subscription.deleted":
        user = await _user_by_customer(db, obj.get("customer"))
        if user is not None:
            await _downgrade_free(db, user)

    elif event_type == "invoice.payment_failed":
        user = await _user_by_customer(db, obj.get("customer"))
        if user is not None:
            logger.warning("Payment failed for user_id=%s", user.id)

    else:
        logger.info("Unhandled Stripe event type: %s", event_type)

    return {"received": True}
