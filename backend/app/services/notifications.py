"""Notification dispatch: SendGrid email, Twilio SMS, Twilio Verify.

Every function logs errors and returns a bool — none of them ever raise, so a
provider outage can't crash a Celery task. PII (emails, phone numbers) is never
logged; we log user_id / outcome only.
"""
from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger("cruisealert.notifications")


# --------------------------------------------------------------------------- #
# Email — SendGrid dynamic templates
# --------------------------------------------------------------------------- #
async def send_email_notification(
    to_email: str,
    template_id: str,
    template_data: dict,
) -> bool:
    """Send a SendGrid dynamic-template email. Returns True on success."""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(from_email=settings.SENDGRID_FROM_EMAIL, to_emails=to_email)
        message.template_id = template_id
        message.dynamic_template_data = template_data

        client = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = client.send(message)  # SDK is synchronous
        ok = 200 <= response.status_code < 300
        if not ok:
            logger.error("SendGrid returned status %s", response.status_code)
        return ok
    except Exception as exc:  # noqa: BLE001
        logger.error("SendGrid send failed: %s", exc)
        return False


# --------------------------------------------------------------------------- #
# SMS — Twilio
# --------------------------------------------------------------------------- #
async def send_sms_notification(to_number: str, message: str) -> bool:
    """Send an SMS via Twilio. Returns True on success.

    The caller is responsible for confirming the recipient has SMS enabled +
    a verified number (see the alert worker / active_alerts_with_context view).
    """
    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        result = client.messages.create(
            body=message,
            from_=settings.TWILIO_FROM_NUMBER,
            to=to_number,
        )
        ok = result.sid is not None
        if not ok:
            logger.error("Twilio message returned no SID")
        return ok
    except Exception as exc:  # noqa: BLE001
        logger.error("Twilio SMS send failed: %s", exc)
        return False


def build_sms_message(
    line: str,
    ship: str,
    sail_date: str,
    cabin: str,
    new_price: str,
    old_price: str,
    short_url: str,
) -> str:
    """Build the <160-char alert SMS body."""
    return (
        f"[CruiseAlert] {line} {ship} {sail_date}: {cabin} dropped to "
        f"${new_price} (was ${old_price}). {short_url} Reply STOP to opt out."
    )


# --------------------------------------------------------------------------- #
# Phone verification — Twilio Verify
# --------------------------------------------------------------------------- #
async def send_phone_verification(phone_e164: str) -> bool:
    """Start a Twilio Verify SMS challenge. Returns True on success."""
    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        verification = client.verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verifications.create(to=phone_e164, channel="sms")
        return verification.status in ("pending", "approved")
    except Exception as exc:  # noqa: BLE001
        logger.error("Twilio Verify start failed: %s", exc)
        return False


async def check_phone_verification(phone_e164: str, code: str) -> bool:
    """Check a Twilio Verify code. Returns True only if approved."""
    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        check = client.verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verification_checks.create(to=phone_e164, code=code)
        return check.status == "approved"
    except Exception as exc:  # noqa: BLE001
        logger.error("Twilio Verify check failed: %s", exc)
        return False
