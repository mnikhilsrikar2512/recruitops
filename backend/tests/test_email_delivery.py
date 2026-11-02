"""Phase 6: email actually leaves the building.

Covers the transport options per port, the never-raise contract, escaping,
and that every flow which issues a link also queues an email for it.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.core import email as email_mod
from app.core.config import settings
from app.core.email import (
    build_notification_email,
    build_password_reset_email,
    build_password_setup_email,
    build_signup_verification_email,
    page_url,
    queue_email,
    send_email,
    smtp_transport_kwargs,
)
from app.schemas.user import UserCreate, UserResetCredentials
from tests.stubs import make_user_record


class Queue:
    def __init__(self) -> None:
        self.tasks: list[tuple] = []

    def add_task(self, fn, *args) -> None:
        self.tasks.append((fn, args))


@pytest.fixture
def smtp_on(monkeypatch):
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "email_from_address", "no-reply@example.com")
    monkeypatch.setattr(settings, "smtp_use_tls", True)


# ---- transport ---------------------------------------------------------------

def test_port_587_uses_starttls_not_implicit_tls(monkeypatch):
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_use_tls", True)
    kw = smtp_transport_kwargs()
    assert kw["use_tls"] is False and kw["start_tls"] is True


def test_port_465_uses_implicit_tls(monkeypatch):
    monkeypatch.setattr(settings, "smtp_port", 465)
    kw = smtp_transport_kwargs()
    assert kw["use_tls"] is True and kw["start_tls"] is False


def test_disabled_email_is_not_sent(monkeypatch):
    monkeypatch.setattr(settings, "email_enabled", False)
    assert asyncio.run(send_email("a@b.com", "s", "<p>h</p>")) is False


def test_send_builds_a_multipart_message(smtp_on, monkeypatch):
    sent = {}

    async def fake_send(message, **kwargs):
        sent["message"], sent["kwargs"] = message, kwargs

    import aiosmtplib
    monkeypatch.setattr(aiosmtplib, "send", fake_send)
    assert asyncio.run(send_email("user@example.com", "Hello", "<p>hi</p>", "hi")) is True
    msg = sent["message"]
    assert msg["To"] == "user@example.com" and msg["Subject"] == "Hello"
    assert "no-reply@example.com" in msg["From"] and msg["Message-ID"]
    assert [p.get_content_type() for p in msg.get_payload()] == ["text/plain", "text/html"]
    assert sent["kwargs"]["hostname"] == "smtp.example.com"


def test_send_never_raises(smtp_on, monkeypatch):
    async def boom(message, **kwargs):
        raise ConnectionRefusedError("smtp down")

    import aiosmtplib
    monkeypatch.setattr(aiosmtplib, "send", boom)
    assert asyncio.run(send_email("user@example.com", "Hello", "<p>hi</p>")) is False


def test_logs_mask_addresses():
    assert email_mod._mask("jane.doe@example.com") == "j***@example.com"


def test_queue_without_background_reports_not_sent():
    assert queue_email(None, "a@b.com", ("s", "h", "t")) is False


# ---- templates ---------------------------------------------------------------

def test_links_point_at_the_real_pages_and_encode_tokens():
    assert page_url("reset-password.html", "a b/c", "https://app.example.com/") == \
        "https://app.example.com/pages/reset-password.html?token=a%20b%2Fc"
    assert "/pages/password-setup.html?token=" in build_password_setup_email("t")[1]
    assert "/pages/reset-password.html?token=" in build_password_reset_email("t")[1]
    assert "/pages/signup-verify.html?token=" in build_signup_verification_email("t")[1]


def test_user_supplied_text_is_escaped():
    _, html_body, _ = build_notification_email("<b>Eve</b>", "x", "<script>alert(1)</script>")
    assert "<script>" not in html_body and "&lt;script&gt;" in html_body
    _, html_body, _ = build_password_setup_email("t", company_name="A&B <Co>", invited_by="<i>x</i>")
    assert "A&amp;B &lt;Co&gt;" in html_body and "<i>x</i>" not in html_body


# ---- flows queue their email ---------------------------------------------------

def test_new_user_gets_an_invitation(monkeypatch):
    from app.services import users as svc

    issued = {}
    monkeypatch.setattr(svc, "find_user_by_email", lambda engine, email: None)
    monkeypatch.setattr(svc, "find_user_by_employee_code", lambda engine, code: None)
    monkeypatch.setattr(svc, "_assert_user_references", lambda engine, **kw: None)
    monkeypatch.setattr(svc, "create_user", lambda engine, payload, pw: make_user_record(
        user_id=41, email="new.person@example.com",
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)))
    monkeypatch.setattr(svc, "mark_unused_password_reset_tokens_used", lambda engine, uid, purposes: None)
    monkeypatch.setattr(svc, "create_password_reset_token", lambda engine, **kw: issued.update(kw))
    queue = Queue()
    payload = UserCreate(full_name="New Person", email="new.person@example.com", employee_code="E-41",
                         primary_location_id=1, primary_role_id=2)
    svc.create_user_service(object(), payload, queue, invited_by="Ada Admin", issued_by_user_id=7)
    assert issued["user_id"] == 41 and issued["purpose"] == "first-password-setup"
    assert issued["issued_by_user_id"] == 7
    (_fn, (to, subject, html_body, _text)), = queue.tasks
    assert to == "new.person@example.com" and "Set Up Your Password" in subject
    assert "Ada Admin" in html_body


def test_admin_setup_link_is_emailed(monkeypatch):
    from app.services import users as svc

    issued = {}
    monkeypatch.setattr(svc, "find_user_by_id", lambda engine, uid: make_user_record(user_id=uid))
    monkeypatch.setattr(svc, "mark_unused_password_reset_tokens_used", lambda engine, uid, purposes: None)
    monkeypatch.setattr(svc, "create_password_reset_token", lambda engine, **kw: issued.update(kw))
    monkeypatch.setattr(svc, "update_user_password_state", lambda engine, **kw: None)
    queue = Queue()
    result = svc.reset_user_credentials_service(object(), 9, UserResetCredentials(mode="setup-link", issued_by_user_id=3), queue)
    assert issued["purpose"] == "admin-reset" and result.setup_token
    (_fn, (to, subject, _h, _t)), = queue.tasks
    assert to == make_user_record(user_id=9).email


def test_password_setup_accepts_invites_and_admin_links(monkeypatch):
    from app.services import auth as svc
    from app.schemas.auth import PasswordSetupRequest

    asked = []

    def finder(engine, token_hash, purpose):
        asked.append(purpose)
        return {"id": 5, "user_id": 22} if purpose == "first-password-setup" else None

    monkeypatch.setattr(svc, "find_valid_password_reset_token", finder)
    monkeypatch.setattr(svc, "update_user_password_state", lambda engine, **kw: None)
    monkeypatch.setattr(svc, "mark_password_reset_token_used", lambda engine, token_id: None)
    phrase = " ".join(["a", "long", "unusual", "passphrase", "91"])  # test value, not a credential
    svc.setup_password_service(object(), PasswordSetupRequest(token="t", new_password=phrase))
    assert asked[0] == "first-password-setup"
