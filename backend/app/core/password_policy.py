"""Password policy (Phase 3.5, PRD §10): NIST-aligned.

- 12–128 characters; no composition rules, no forced rotation.
- Refused when the password, or its letters-only core ("Password2024!" →
  "password"), is a commonly used / breached password (bundled list), or
  when it is a single repeated character.
- Optional online breach check against Have I Been Pwned (k-anonymity range
  API: only the first 5 hex chars of the SHA-1 leave the server) when
  PASSWORD_BREACH_CHECK=hibp. If HIBP can't be reached the bundled list
  still applies (fail open on the network, never on the policy).
"""
from __future__ import annotations

import hashlib
import re
import urllib.request
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

MIN_LENGTH = 12
MAX_LENGTH = 128


@lru_cache(maxsize=1)
def _common_passwords() -> frozenset[str]:
    path = Path(__file__).with_name("common_passwords.txt")
    lines = path.read_text(encoding="utf-8").splitlines()
    return frozenset(line.strip().lower() for line in lines if line.strip() and not line.startswith("#"))


def _breached_online(password: str) -> bool:
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()  # noqa: S324 — HIBP protocol
    prefix, suffix = digest[:5], digest[5:]
    request = urllib.request.Request(
        f"https://api.pwnedpasswords.com/range/{prefix}", headers={"Add-Padding": "true", "User-Agent": "RecruitOps"}
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:  # noqa: S310 — fixed https URL
            body = response.read().decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001 — network failure: the offline list still applied
        return False
    for line in body.splitlines():
        candidate, _, count = line.partition(":")
        if candidate.strip() == suffix and count.strip() not in ("", "0"):
            return True
    return False


def password_problem(password: str) -> str | None:
    """None when acceptable, else a message safe to show the user."""
    if len(password) < MIN_LENGTH:
        return f"Password must be at least {MIN_LENGTH} characters"
    if len(password) > MAX_LENGTH:
        return f"Password must be at most {MAX_LENGTH} characters"
    if len(set(password)) == 1:
        return "Password cannot be a single repeated character"
    lowered = password.lower()
    core = re.sub(r"[^a-z]", "", lowered)
    common = _common_passwords()
    if lowered in common or (core and core in common):
        return "This password is too common or has appeared in a data breach — choose another"
    if settings.password_breach_check == "hibp" and _breached_online(password):
        return "This password has appeared in a data breach — choose another"
    return None


def validate_new_password(password: str) -> str:
    """Pydantic validator helper: returns the password or raises ValueError."""
    problem = password_problem(password)
    if problem:
        raise ValueError(problem)
    return password
