"""Outbound email (Phase 6: real delivery).

Every message goes through ``send_email``. Request handlers queue it with
FastAPI ``BackgroundTasks`` (``queue_email``) so a slow or broken SMTP server
never delays or fails the request that triggered it; scripts call
``send_email_sync``.

Transport: plain SMTP, so any provider works (SendGrid, Amazon SES, Azure
Communication Services, Postmark, Mailgun, a company relay). Port 465 uses
implicit TLS; any other port upgrades with STARTTLS when ``SMTP_USE_TLS`` is
true (the default, and required in staging/production).

Links point at the static pages under ``/pages/`` on ``FRONTEND_BASE_URL``.
Everything interpolated into HTML is escaped.
"""
from __future__ import annotations

import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid
from html import escape
from typing import Any
from urllib.parse import quote

from app.core.config import settings

logger = logging.getLogger("recruitops.email")

EmailMessage = tuple[str, str, str]  # (subject, html_body, text_body)


def _mask(address: str) -> str:
    """Keep addresses out of logs in full: ``j***@example.com``."""
    local, _, domain = address.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


def smtp_transport_kwargs() -> dict[str, Any]:
    """aiosmtplib connection options for the configured port."""
    implicit_tls = settings.smtp_port == 465
    return {
        "hostname": settings.smtp_host,
        "port": settings.smtp_port,
        "username": settings.smtp_user or None,
        "password": settings.smtp_password or None,
        "use_tls": implicit_tls,
        "start_tls": False if implicit_tls else bool(settings.smtp_use_tls),
        "timeout": settings.smtp_timeout_seconds,
    }


def build_mime(to_email: str, subject: str, html_body: str, text_body: str | None) -> MIMEMultipart:
    message = MIMEMultipart("alternative")
    message["From"] = formataddr((settings.email_from_name, settings.email_from_address))
    message["To"] = to_email
    message["Subject"] = subject
    message["Message-ID"] = make_msgid(domain=(settings.email_from_address.partition("@")[2] or None))
    if settings.email_reply_to:
        message["Reply-To"] = settings.email_reply_to
    if text_body:
        message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))
    return message


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> bool:
    """Send one message. Never raises: returns False and logs on failure."""
    if not settings.email_enabled:
        logger.info("email disabled; not sending to=%s subject=%s", _mask(to_email), subject)
        return False
    if not settings.smtp_host or not settings.email_from_address:
        logger.warning("SMTP not configured; cannot send to=%s subject=%s", _mask(to_email), subject)
        return False
    try:
        import aiosmtplib

        await aiosmtplib.send(build_mime(to_email, subject, html_body, text_body), **smtp_transport_kwargs())
        logger.info("email sent to=%s subject=%s", _mask(to_email), subject)
        return True
    except Exception:
        logger.exception("email failed to=%s subject=%s", _mask(to_email), subject)
        return False


def send_email_sync(to_email: str, message: EmailMessage) -> bool:
    """For scripts (no event loop running)."""
    subject, html_body, text_body = message
    return asyncio.run(send_email(to_email, subject, html_body, text_body))


def queue_email(background: Any, to_email: str, message: EmailMessage) -> bool:
    """Queue a message to send after the response. Returns False (and logs)
    when there is no BackgroundTasks to queue on, e.g. a direct service call."""
    if background is None:
        logger.warning("no background queue; email not sent to=%s subject=%s", _mask(to_email), message[0])
        return False
    subject, html_body, text_body = message
    background.add_task(send_email, to_email, subject, html_body, text_body)
    return True


# ---- templates --------------------------------------------------------------

def page_url(page: str, token: str | None = None, base_url: str | None = None) -> str:
    base = (base_url or settings.frontend_base_url).rstrip("/")
    url = f"{base}/pages/{page}"
    return f"{url}?token={quote(token, safe='')}" if token is not None else url


def _layout(heading: str, paragraphs: list[str], button: tuple[str, str] | None = None, footer: str = "") -> str:
    """Minimal, inline-styled HTML that renders in every mail client.
    ``paragraphs`` and ``footer`` must already be escaped."""
    body = "".join(f'<p style="margin:0 0 14px;line-height:1.5">{p}</p>' for p in paragraphs)
    if button:
        label, href = button
        body += (
            f'<p style="margin:22px 0"><a href="{escape(href, quote=True)}" '
            'style="background:#a3542f;color:#ffffff;text-decoration:none;padding:11px 20px;'
            f'border-radius:6px;display:inline-block;font-weight:600">{escape(label)}</a></p>'
            '<p style="margin:0 0 14px;font-size:13px;color:#6b6b6b">If the button doesn\'t work, '
            f'copy this link into your browser:<br><span style="word-break:break-all">{escape(href)}</span></p>'
        )
    foot = f'<p style="margin:24px 0 0;font-size:12px;color:#8a8a8a">{footer}</p>' if footer else ""
    return (
        '<!doctype html><html><body style="margin:0;padding:24px;background:#f6f4f1;'
        'font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#1f1f1f">'
        '<div style="max-width:560px;margin:0 auto;background:#ffffff;border-radius:10px;padding:28px">'
        '<div style="font-weight:700;font-size:18px;margin-bottom:18px">RecruitOps</div>'
        f'<h1 style="font-size:20px;margin:0 0 16px">{escape(heading)}</h1>{body}{foot}'
        "</div></body></html>"
    )


def _hours(hours: int | None) -> int:
    return int(hours if hours is not None else settings.token_expiry_hours)


def build_password_setup_email(
    setup_token: str,
    base_url: str | None = None,
    *,
    company_name: str | None = None,
    invited_by: str | None = None,
    expires_in_hours: int | None = None,
) -> EmailMessage:
    """Invitation for a new user, or a setup link an admin re-issued."""
    url = page_url("password-setup.html", setup_token, base_url)
    hours = _hours(expires_in_hours)
    subject = "Set Up Your Password - RecruitOps"
    who = f" by {escape(invited_by)}" if invited_by else ""
    where = f" for {escape(company_name)}" if company_name else ""
    html_body = _layout(
        "Set up your RecruitOps account",
        [f"An account has been created for you{where}{who}.",
         f"Choose a password to finish setting it up. This link expires in {hours} hours and works once."],
        ("Set your password", url),
        "If you weren't expecting this email, you can ignore it.",
    )
    text_body = (
        f"Set up your RecruitOps account\n\n"
        f"An account has been created for you{(' for ' + company_name) if company_name else ''}.\n"
        f"Set your password here: {url}\n\n"
        f"This link expires in {hours} hours and works once.\n"
    )
    return subject, html_body, text_body


def build_password_reset_email(
    reset_token: str,
    base_url: str | None = None,
    *,
    expires_in_hours: int | None = None,
) -> EmailMessage:
    url = page_url("reset-password.html", reset_token, base_url)
    hours = _hours(expires_in_hours)
    subject = "Reset Your Password - RecruitOps"
    html_body = _layout(
        "Reset your password",
        ["We received a request to reset the password for your RecruitOps account.",
         f"This link expires in {hours} hours and works once."],
        ("Reset your password", url),
        "If you didn't ask for this, ignore this email. Your password won't change.",
    )
    text_body = (
        "Reset your password\n\n"
        f"Reset your RecruitOps password here: {url}\n\n"
        f"This link expires in {hours} hours and works once.\n"
        "If you didn't ask for this, ignore this email.\n"
    )
    return subject, html_body, text_body


def build_signup_verification_email(token: str, base_url: str | None = None) -> EmailMessage:
    url = page_url("signup-verify.html", token, base_url)
    subject = "Confirm your email to finish setting up RecruitOps"
    html_body = _layout(
        "Confirm your email address",
        ["Welcome to RecruitOps.",
         "Confirm your email address to finish setting up your company. The link works for 24 hours."],
        ("Confirm email address", url),
        "If you didn't sign up, ignore this email.",
    )
    text_body = f"Welcome to RecruitOps.\n\nConfirm your email address: {url}\n\nThe link works for 24 hours.\n"
    return subject, html_body, text_body


def build_notification_email(
    user_name: str,
    event_type: str,
    message: str,
    action_url: str | None = None,
    base_url: str | None = None,
) -> EmailMessage:
    base = (base_url or settings.frontend_base_url).rstrip("/")
    subject = f"Notification: {event_type.replace('_', ' ').title()} - RecruitOps"
    html_body = _layout(
        f"Hi {user_name}",
        [escape(message)],
        ("View details", f"{base}{action_url}") if action_url else None,
    )
    text_body = f"Notification for {user_name}\n\n{message}\n" + (f"\n{base}{action_url}\n" if action_url else "")
    return subject, html_body, text_body
