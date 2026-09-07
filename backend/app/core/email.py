from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> bool:
    if not settings.email_enabled:
        logger.info("Email sending is disabled. Would send to=%s subject=%s", to_email, subject)
        return False

    if not settings.smtp_host or not settings.email_from_address:
        logger.warning("SMTP not configured. Cannot send email to=%s", to_email)
        return False

    try:
        import aiosmtplib

        message = MIMEMultipart("alternative")
        message["From"] = f"{settings.email_from_name} <{settings.email_from_address}>"
        message["To"] = to_email
        message["Subject"] = subject

        if text_body:
            message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            use_tls=settings.smtp_use_tls,
        )
        logger.info("Email sent successfully to=%s subject=%s", to_email, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to=%s subject=%s", to_email, subject)
        return False


def build_password_setup_email(setup_token: str, base_url: str = "http://localhost:3000") -> tuple[str, str, str]:
    subject = "Set Up Your Password - Recruitment System"
    setup_url = f"{base_url}/password-setup?token={setup_token}"
    html_body = f"""
    <html>
    <body>
        <h2>Welcome to Recruitment System</h2>
        <p>An account has been created for you. Please set your password using the link below:</p>
        <p><a href="{setup_url}">Set Your Password</a></p>
        <p>This link will expire in 24 hours.</p>
        <p>If you did not expect this email, please ignore it.</p>
    </body>
    </html>
    """
    text_body = (
        f"Welcome to Recruitment System\n\n"
        f"Set your password here: {setup_url}\n\n"
        f"This link will expire in 24 hours.\n"
    )
    return subject, html_body, text_body


def build_password_reset_email(reset_token: str, base_url: str = "http://localhost:3000") -> tuple[str, str, str]:
    subject = "Reset Your Password - Recruitment System"
    reset_url = f"{base_url}/reset-password?token={reset_token}"
    html_body = f"""
    <html>
    <body>
        <h2>Password Reset Request</h2>
        <p>We received a request to reset your password. Use the link below:</p>
        <p><a href="{reset_url}">Reset Your Password</a></p>
        <p>This link will expire in 24 hours.</p>
        <p>If you did not request this, please ignore this email.</p>
    </body>
    </html>
    """
    text_body = (
        f"Password Reset Request\n\n"
        f"Reset your password here: {reset_url}\n\n"
        f"This link will expire in 24 hours.\n"
    )
    return subject, html_body, text_body


def build_notification_email(
    user_name: str,
    event_type: str,
    message: str,
    action_url: str | None = None,
    base_url: str = "http://localhost:3000",
) -> tuple[str, str, str]:
    subject = f"Notification: {event_type.replace('_', ' ').title()} - Recruitment System"
    action_link = f'<p><a href="{base_url}{action_url}">View Details</a></p>' if action_url else ""
    html_body = f"""
    <html>
    <body>
        <h2>Notification for {user_name}</h2>
        <p>{message}</p>
        {action_link}
    </body>
    </html>
    """
    text_body = f"Notification for {user_name}\n\n{message}\n"
    return subject, html_body, text_body
