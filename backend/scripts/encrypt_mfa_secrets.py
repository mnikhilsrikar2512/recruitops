"""Encrypt two-step verification seeds at rest, and re-wrap them after a key
rotation (Phase 6.3). Safe to run any time, any number of times.

    cd backend && .venv/bin/python scripts/encrypt_mfa_secrets.py --dry-run
    cd backend && .venv/bin/python scripts/encrypt_mfa_secrets.py

Rewrites every row that is still plaintext or encrypted under a key that
isn't the current (first) one in MFA_ENCRYPTION_KEYS. Each row is updated
only if it hasn't changed since it was read, so it can run while users are
enrolling. Needs migration 032 first.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def rewrap_all(engine, dry_run: bool = False) -> dict[str, int]:
    from sqlalchemy import text

    from app.core.secret_box import decrypt, encrypt, is_encrypted, mfa_context, needs_rewrap

    counts = {"checked": 0, "encrypted": 0, "rewrapped": 0, "skipped_changed": 0}
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT user_id, totp_secret FROM dbo.user_mfa")).all()
    for user_id, stored in rows:
        counts["checked"] += 1
        if not needs_rewrap(stored):
            continue
        context = mfa_context(user_id)
        fresh = encrypt(decrypt(stored, context), context)
        kind = "rewrapped" if is_encrypted(stored) else "encrypted"
        if dry_run:
            counts[kind] += 1
            continue
        with engine.begin() as connection:
            result = connection.execute(
                text("UPDATE dbo.user_mfa SET totp_secret = :new WHERE user_id = :u AND totp_secret = :old"),
                {"new": fresh, "u": user_id, "old": stored},
            )
        counts[kind if (result.rowcount or 0) == 1 else "skipped_changed"] += 1
    return counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="count what would change; write nothing")
    opts = ap.parse_args()
    from app.core.secret_box import current_key_id
    from app.db.session import create_db_engine

    counts = rewrap_all(create_db_engine(), dry_run=opts.dry_run)
    verb = "would change" if opts.dry_run else "changed"
    print(f"✓ checked {counts['checked']} enrolments under key {current_key_id()!r}; {verb}: "
          f"{counts['encrypted']} plaintext → encrypted, {counts['rewrapped']} re-wrapped"
          + (f"; {counts['skipped_changed']} changed meanwhile (run again)" if counts["skipped_changed"] else ""))


if __name__ == "__main__":
    main()
