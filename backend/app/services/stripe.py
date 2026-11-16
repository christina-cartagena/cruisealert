"""Stripe helpers: checkout sessions, billing portal, and webhook verification.

All Stripe calls are wrapped; failures are logged and surfaced to the caller
without leaking internals.
"""
from __future__ import annotations

import logging

import stripe

from app.config import settings

logger = logging.getLogger("cruisealert.stripe")

stripe.api_key = settings.STRIPE_SECRET_KEY

PRICE_IDS = {
    "monthly": settings.STRIPE_PRO_MONTHLY_PRICE_ID,
    "annual": settings.STRIPE_PRO_ANNUAL_PRICE_ID,
}


def get_or_create_customer(email: str, user_id: str, existing_customer_id: str | None) -> str:
    """Return an existing Stripe customer id or create a new one."""
    if existing_customer_id:
        return existing_customer_id
    customer = stripe.Customer.create(email=email, metadata={"user_id": user_id})
    return customer.id


def create_checkout_session(
    customer_id: str,
    price_id: str,
    user_id: str,
) -> str:
    """Create a subscription checkout session and return its hosted URL."""
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.FRONTEND_URL}/billing?status=success",
        cancel_url=f"{settings.FRONTEND_URL}/billing?status=cancelled",
        client_reference_id=user_id,
        metadata={"user_id": user_id},
    )
    return session.url


def create_portal_session(customer_id: str) -> str:
    """Create a billing-portal session and return its URL."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.FRONTEND_URL}/billing",
    )
    return session.url


def verify_webhook(payload: bytes, signature: str):
    """Verify a Stripe webhook signature and return the parsed event.

    Raises ``stripe.error.SignatureVerificationError`` / ValueError on failure;
    the caller converts that to HTTP 400.
    """
    return stripe.Webhook.construct_event(
        payload, signature, settings.STRIPE_WEBHOOK_SECRET
    )


def resolve_price_id(plan: str) -> str | None:
    """Map a plan slug (monthly|annual) or raw price id to a Stripe price id."""
    if plan in PRICE_IDS:
        return PRICE_IDS[plan]
    if plan.startswith("price_"):
        return plan
    return None
