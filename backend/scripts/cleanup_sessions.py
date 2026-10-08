"""Delete sign-ins (and their refresh tokens) that ended more than N days ago.

Plan 3.3 scheduled cleanup. Run daily (cron / scheduler):
    cd backend && .venv/bin/python scripts/cleanup_sessions.py --days 30
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import create_db_engine  # noqa: E402
from app.repositories.auth import purge_stale_sessions  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    opts = ap.parse_args()
    removed = purge_stale_sessions(create_db_engine(), opts.days)
    print(f"✓ removed {removed} ended sessions older than {opts.days} days")


if __name__ == "__main__":
    main()
