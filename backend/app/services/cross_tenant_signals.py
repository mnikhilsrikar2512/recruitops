"""Lightweight cross-company duplicate-submission signal (030).

Two separate RecruitOps companies (tenants) can both be working the same
end client and submit the same candidate to them around the same time.
Each company's candidate data is intentionally walled off from every
other company's — that is the whole point of tenancy — so this module
never compares raw candidate records across companies. It only ever
stores and compares salted hashes of the candidate's email/phone plus a
normalized client name: enough to say "someone else already submitted a
profile that looks like this one, to a client with this name, recently"
without naming the other company or revealing any of its data.

Called once, right after a candidate is finalized into a requisition
(app/services/candidates.py::finalize_candidate_service). Never blocks
or fails that flow — a problem here is a missed flag, not a broken
finalize.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import Engine, text

from app.core.config import settings

SIGNAL_WINDOW_DAYS = 90


@dataclass
class CrossTenantSignal:
    flagged: bool
    other_vendor_submissions: int = 0
    most_recent_days_ago: int | None = None


def _normalize_client_name(name: str | None) -> str:
    if not name:
        return ""
    collapsed = re.sub(r"\s+", " ", name).strip().lower()
    return re.sub(r"[^\w\s]", "", collapsed)


def _normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    value = email.strip().lower()
    return value or None


def _normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    # Last 10 digits: ignores +country-code / leading-zero spelling
    # differences between how two companies stored the same number.
    return digits[-10:] if len(digits) >= 7 else None


def _hash(value: str) -> str:
    pepper = (settings.jwt_signing_key or "dev-only-cross-tenant-signal-pepper").encode("utf-8")
    return hmac.new(pepper, f"cross-tenant-signal:{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def check_and_record_cross_tenant_signal(
    engine: Engine,
    *,
    tenant_id: int | None,
    candidate_id: int,
    requisition_id: int,
    application_id: int | None,
    email: str | None,
    phone: str | None,
    client_name: str | None,
) -> CrossTenantSignal | None:
    """Record this submission's signal and flag if another tenant already
    submitted a matching one for the same (normalized) client recently.

    Returns None when there isn't enough to key on (no client name, or
    neither email nor phone) — not every finalize produces a signal.
    """
    if tenant_id is None:
        return None
    client_norm = _normalize_client_name(client_name)
    if not client_norm:
        return None
    email_hash = _hash(e) if (e := _normalize_email(email)) else None
    phone_hash = _hash(p) if (p := _normalize_phone(phone)) else None
    if not email_hash and not phone_hash:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(days=SIGNAL_WINDOW_DAYS)

    with engine.begin() as connection:
        existing = connection.execute(
            text(
                """
                SELECT TOP 1 s.created_at,
                  (SELECT COUNT(*) FROM dbo.cross_tenant_submission_signals AS s2
                   WHERE s2.client_name_norm = :client_norm
                     AND s2.tenant_id <> :tenant_id
                     AND s2.created_at >= :cutoff
                     AND ((:email_hash IS NOT NULL AND s2.email_hash = :email_hash)
                       OR (:phone_hash IS NOT NULL AND s2.phone_hash = :phone_hash))
                  ) AS other_count
                FROM dbo.cross_tenant_submission_signals AS s
                WHERE s.client_name_norm = :client_norm
                  AND s.tenant_id <> :tenant_id
                  AND s.created_at >= :cutoff
                  AND ((:email_hash IS NOT NULL AND s.email_hash = :email_hash)
                    OR (:phone_hash IS NOT NULL AND s.phone_hash = :phone_hash))
                ORDER BY s.created_at DESC;
                """
            ),
            {
                "client_norm": client_norm,
                "tenant_id": tenant_id,
                "cutoff": cutoff,
                "email_hash": email_hash,
                "phone_hash": phone_hash,
            },
        ).mappings().first()

        connection.execute(
            text(
                """
                INSERT INTO dbo.cross_tenant_submission_signals
                  (tenant_id, candidate_id, requisition_id, application_id, email_hash, phone_hash, client_name_norm)
                VALUES
                  (:tenant_id, :candidate_id, :requisition_id, :application_id, :email_hash, :phone_hash, :client_norm);
                """
            ),
            {
                "tenant_id": tenant_id,
                "candidate_id": candidate_id,
                "requisition_id": requisition_id,
                "application_id": application_id,
                "email_hash": email_hash,
                "phone_hash": phone_hash,
                "client_norm": client_norm,
            },
        )

    if not existing:
        return CrossTenantSignal(flagged=False)
    created_at = existing["created_at"]
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    days_ago = max((datetime.now(timezone.utc) - created_at).days, 0)
    return CrossTenantSignal(
        flagged=True,
        other_vendor_submissions=int(existing["other_count"] or 0),
        most_recent_days_ago=days_ago,
    )
