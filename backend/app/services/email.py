from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings


logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    pass


def send_email(*, to_email: str, subject: str, body: str) -> None:
    if settings.email_delivery_mode.lower() != "smtp":
        logger.info(
            "Demo email mode: message for %s with subject %r:\n%s",
            to_email,
            subject,
            body,
        )
        return

    if not settings.smtp_host:
        raise EmailDeliveryError("SMTP_HOST is required when EMAIL_DELIVERY_MODE=smtp")

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        smtp_class = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
        with smtp_class(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls and not settings.smtp_use_ssl:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError(str(exc)) from exc
