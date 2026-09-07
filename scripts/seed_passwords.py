#!/usr/bin/env python3
"""Set known passwords for all seed users so login works immediately.

Usage: cd backend && .venv/bin/python ../scripts/seed_passwords.py

All users get password: admin123
"""
import sys
sys.path.insert(0, ".")

from app.core.security import create_sha256_password_hash
from app.db.session import create_db_engine
from sqlalchemy import text

KNOWN_PASSWORD = "admin123"

def main():
    engine = create_db_engine()
    password_hash = create_sha256_password_hash(KNOWN_PASSWORD)

    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE users SET password_hash = :h, updated_at = SYSUTCDATETIME() WHERE password_hash != :h"),
            {"h": password_hash},
        )
        updated = result.rowcount

        rows = conn.execute(
            text("SELECT id, full_name, email FROM users ORDER BY id")
        ).mappings().all()

    print(f"Updated {updated} user(s) with password: {KNOWN_PASSWORD}\n")
    print(f"{'ID':<5} {'Name':<30} {'Email'}")
    print("-" * 70)
    for r in rows:
        print(f"{r['id']:<5} {(r['full_name'] or ''):<30} {r['email']}")

if __name__ == "__main__":
    main()
