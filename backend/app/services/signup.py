"""Self-serve signup (Phase 5.2; decisions D-01 revised, D-09).

1. POST /signup — company, head office and first Admin are created with the
   company 'pending'; the legal documents are accepted at the versions shown;
   a verification link (24 h) is emailed.
2. POST /signup/verify — the link proves the address. With two-step
   verification required for admins (staging/production) the next step is
   enrolment; otherwise the company becomes active straight away.
3. POST /signup/mfa/start + /signup/mfa/confirm — with the short-lived setup
   token from step 2; on success the company becomes active.
Then the admin signs in normally.

Anti-abuse: per-IP rate limits, a honeypot field, generic answers that
don't reveal whether an email is registered.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import Engine, text

from app.core.config import settings
from app.core.security import generate_session_token, hash_password, hash_session_token
from app.core.tokens import InvalidToken, decode_signup_token, issue_signup_token
from app.core.totp import hash_recovery_code, matching_step, new_recovery_codes, new_secret, otpauth_uri
from app.repositories.legal import list_active_documents
from app.repositories.mfa import confirm_enrollment, find_mfa, start_enrollment
from app.repositories.users import create_password_reset_token, find_valid_password_reset_token, mark_password_reset_token_used
from app.schemas.signup import SignupRequest
from app.services.provisioning import EmailTaken, provision_company, record_signup_acceptances
from app.services.tenants import ActivationBlocked, activate_tenant

logger = logging.getLogger("recruitops.signup")
PURPOSE = "signup-verify"
GENERIC = "Check your email: we've sent a link to confirm your address and finish setting up your company."


def _verification_email(token: str) -> tuple[str, str, str]:
    url = f"{settings.frontend_base_url}/pages/signup-verify.html?token={token}"
    subject = "Confirm your email to finish setting up RecruitOps"
    html = (f"<p>Welcome to RecruitOps.</p><p><a href=\"{url}\">Confirm your email address</a> to finish setting up "
            "your company. The link works for 24 hours.</p><p>If you didn't sign up, ignore this email.</p>")
    text_body = f"Welcome to RecruitOps.\n\nConfirm your email address: {url}\n\nThe link works for 24 hours."
    return subject, html, text_body


def _issue_verification(engine: Engine, user_id: int) -> str:
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE dbo.password_reset_tokens SET used_at = SYSUTCDATETIME() "
            "WHERE user_id = :u AND purpose = :p AND used_at IS NULL;"), {"u": user_id, "p": PURPOSE})
    token = generate_session_token()
    create_password_reset_token(engine, user_id=user_id, token_hash=hash_session_token(token), purpose=PURPOSE,
                                issued_by_user_id=None, expires_at=datetime.now(timezone.utc) + timedelta(hours=24))
    return token


def _send(background: BackgroundTasks | None, email: str, token: str) -> None:
    from app.core.email import send_email

    subject, html, text_body = _verification_email(token)
    if background is not None:
        background.add_task(send_email, email, subject, html, text_body)


def _dev(token: str | None) -> str | None:
    return None if settings.is_production else token


def signup_service(engine: Engine, payload: SignupRequest, background: BackgroundTasks | None,
                   ip: str | None, user_agent: str | None):
    from app.schemas.signup import SignupAccepted

    if payload.website:  # honeypot: answer like a success, create nothing
        return SignupAccepted(message=GENERIC)
    current = {doc["doc_type"]: doc["version"] for doc in list_active_documents(engine)}
    if not current or any(payload.accepted.get(doc_type) != version for doc_type, version in current.items()):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="Please accept the current Terms, Privacy Policy and Data Processing Addendum")
    try:
        created = provision_company(
            engine, company_name=payload.company_name, admin_name=payload.admin_name, admin_email=payload.email,
            city=payload.city, password_hash=hash_password(payload.password), password_ready=True,
            onboarding="self_serve", email_verified=False,
        )
    except EmailTaken:
        # Don't reveal that the address is registered; that person gets no new company.
        logger.info("signup attempted for an existing email")
        return SignupAccepted(message=GENERIC)
    record_signup_acceptances(engine, tenant_id=created["tenant_id"], user_id=created["admin_id"],
                              accepted=payload.accepted, ip=ip, user_agent=user_agent)
    token = _issue_verification(engine, created["admin_id"])
    _send(background, payload.email, token)
    return SignupAccepted(message=GENERIC, dev_verify_token=_dev(token))


def resend_service(engine: Engine, email: str, background: BackgroundTasks | None):
    from app.schemas.signup import SignupAccepted

    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT u.id FROM dbo.users u JOIN dbo.tenants t ON t.id = u.tenant_id "
            "WHERE u.email = :e AND u.email_verified_at IS NULL AND t.status = N'pending' AND t.onboarding = N'self_serve'"),
            {"e": email.strip().lower()}).first()
    if row is None:
        return SignupAccepted(message=GENERIC)
    token = _issue_verification(engine, int(row[0]))
    _send(background, email, token)
    return SignupAccepted(message=GENERIC, dev_verify_token=_dev(token))


def _tenant_of(engine: Engine, user_id: int) -> tuple[int, str]:
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT t.id, t.status FROM dbo.users u JOIN dbo.tenants t ON t.id = u.tenant_id WHERE u.id = :u"), {"u": user_id}).one()
    return int(row[0]), str(row[1])


def _activate_without_mfa(engine: Engine, tenant_id: int) -> None:
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE dbo.tenants SET status = N'active', updated_at = SYSUTCDATETIME() WHERE id = :t AND status = N'pending'"),
            {"t": tenant_id})


def verify_service(engine: Engine, token: str):
    from app.schemas.signup import VerifyResponse

    record = find_valid_password_reset_token(engine, hash_session_token(token), PURPOSE)
    if not record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This link has expired or was already used. Ask for a new one from the sign-up page.")
    mark_password_reset_token_used(engine, int(record["id"]))
    user_id = int(record["user_id"])
    with engine.begin() as connection:
        connection.execute(text("UPDATE dbo.users SET email_verified_at = SYSUTCDATETIME(), updated_at = SYSUTCDATETIME() "
                                "WHERE id = :u AND email_verified_at IS NULL"), {"u": user_id})
    tenant_id, tenant_status = _tenant_of(engine, user_id)
    if tenant_status == "pending" and not settings.mfa_enforce_admin_enrollment:
        _activate_without_mfa(engine, tenant_id)
        return VerifyResponse(next="login", company_status="active")
    if tenant_status != "pending":
        return VerifyResponse(next="login", company_status=tenant_status)
    setup_token, _ = issue_signup_token(user_id=user_id, tenant_id=tenant_id)
    return VerifyResponse(next="mfa", company_status="pending", setup_token=setup_token)


def _from_setup_token(engine: Engine, setup_token: str) -> tuple[int, int, str]:
    try:
        claims = decode_signup_token(setup_token)
    except InvalidToken:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="This setup step has timed out. Open the link from your email again.") from None
    user_id = int(claims["sub"])
    tenant_id, tenant_status = _tenant_of(engine, user_id)
    if str(tenant_id) != str(claims["tid"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid setup token")
    with engine.connect() as connection:
        email = connection.execute(text("SELECT email FROM dbo.users WHERE id = :u"), {"u": user_id}).scalar_one()
    return user_id, tenant_id, str(email) if tenant_status == "pending" else ""


def mfa_start_service(engine: Engine, setup_token: str):
    from app.schemas.signup import MfaStartResponse

    user_id, _tenant_id, email = _from_setup_token(engine, setup_token)
    if not email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This company is already set up; sign in instead")
    existing = find_mfa(engine, user_id)
    if existing is not None and existing.enabled_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Two-step verification is already set up")
    secret = new_secret()
    start_enrollment(engine, user_id, secret)
    return MfaStartResponse(secret=secret, otpauth_uri=otpauth_uri(secret, email))


def mfa_confirm_service(engine: Engine, setup_token: str, code: str):
    from app.schemas.signup import MfaConfirmResponse

    user_id, tenant_id, email = _from_setup_token(engine, setup_token)
    if not email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This company is already set up; sign in instead")
    mfa = find_mfa(engine, user_id)
    if mfa is None or mfa.enabled_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Start the set-up first")
    step = matching_step(mfa.totp_secret, code or "")
    if step is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That code doesn't match — check the app and try again")
    codes = new_recovery_codes()
    confirm_enrollment(engine, user_id, step, [hash_recovery_code(c) for c in codes])
    try:
        activate_tenant(engine, tenant_id)
        company_status = "active"
    except ActivationBlocked:
        company_status = "pending"
    return MfaConfirmResponse(recovery_codes=codes, company_status=company_status)
