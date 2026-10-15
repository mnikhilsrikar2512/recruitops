"""Unit tests for the 030 cross-tenant duplicate-submission signal's pure
helpers — no database needed, so these always run (unlike the *_db.py
suite, which is skipped when the configured database is unreachable).
"""
from __future__ import annotations

from app.services.cross_tenant_signals import (
    _hash,
    _normalize_client_name,
    _normalize_email,
    _normalize_phone,
)


def test_normalize_client_name_collapses_punctuation_case_and_spacing():
    assert _normalize_client_name("  Acme   Corp, Inc. ") == "acme corp inc"
    assert _normalize_client_name(None) == ""
    assert _normalize_client_name("") == ""


def test_normalize_client_name_treats_near_spellings_the_same():
    assert _normalize_client_name("Acme Corp") == _normalize_client_name("ACME   CORP")
    assert _normalize_client_name("Acme Corp.") == _normalize_client_name("Acme Corp")


def test_normalize_email_lowercases_and_trims():
    assert _normalize_email(" John.Doe@Acme.com ") == "john.doe@acme.com"
    assert _normalize_email(None) is None
    assert _normalize_email("") is None


def test_normalize_phone_keeps_last_ten_digits_regardless_of_formatting():
    assert _normalize_phone("+1 (555) 123-4567") == "5551234567"
    assert _normalize_phone("0091-98765-43210") == "9876543210"
    # Two spellings of the same number end up identical.
    assert _normalize_phone("+91 98765 43210") == _normalize_phone("09876543210")


def test_normalize_phone_rejects_too_short_values():
    assert _normalize_phone("12345") is None
    assert _normalize_phone(None) is None


def test_hash_is_deterministic_and_does_not_round_trip():
    h1 = _hash("john.doe@acme.com")
    h2 = _hash("john.doe@acme.com")
    assert h1 == h2
    assert h1 != "john.doe@acme.com"
    assert len(h1) == 64  # sha256 hex digest

    # Different inputs hash differently.
    assert _hash("jane.doe@acme.com") != h1
