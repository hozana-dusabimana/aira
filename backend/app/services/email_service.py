"""SMTP email delivery for password resets, email verification, etc.

Disabled by default. When ``EMAIL_ENABLED=false`` (the default), messages
are logged at INFO level instead of being sent — handy for development
where you can read the reset code straight off the server log.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(*, to: str, subject: str, body: str, html: str | None = None) -> bool:
    """Returns True on success, False on failure. Never raises."""
    if not settings.EMAIL_ENABLED:
        logger.info("[email-disabled] to=%s subject=%s\n%s", to, subject, body)
        return False

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        if settings.SMTP_USE_TLS:
            server: smtplib.SMTP = smtplib.SMTP(
                settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT,
            )
            server.starttls()
        else:
            server = smtplib.SMTP(
                settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT,
            )
        with server:
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Sent email to=%s subject=%s", to, subject)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Email delivery failed to=%s: %s", to, exc)
        return False


def send_password_reset_code(*, to: str, full_name: str, code: str) -> bool:
    subject = "Your AIRA password reset code"
    body = (
        f"Hello {full_name},\n\n"
        f"Use this code to reset your AIRA password: {code}\n"
        f"It expires in 15 minutes.\n\n"
        f"If you did not request this, you can ignore this email.\n"
    )
    html = (
        f"<p>Hello {full_name},</p>"
        f"<p>Use this code to reset your AIRA password:</p>"
        f"<p style='font-size:24px;font-weight:600;letter-spacing:4px'>{code}</p>"
        f"<p>It expires in 15 minutes. If you did not request this, you can ignore this email.</p>"
    )
    return send_email(to=to, subject=subject, body=body, html=html)


def send_verification_code(*, to: str, full_name: str, code: str) -> bool:
    subject = "Verify your AIRA email"
    body = (
        f"Hello {full_name},\n\n"
        f"Your AIRA email verification code is: {code}\n"
        f"It expires in 24 hours.\n"
    )
    return send_email(to=to, subject=subject, body=body)
