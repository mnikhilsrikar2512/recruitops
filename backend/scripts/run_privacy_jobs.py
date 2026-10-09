"""Privacy job runner (Phase 5.3). Run every hour (cron / scheduled task):

    cd backend && .venv/bin/python scripts/run_privacy_jobs.py

- purges companies whose approved delete request is past its 7-day cooling-off
- deletes held audit rows past their hold date (default 90 days)
- removes export zips past their 7-day download window
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    from app.db.session import create_db_engine
    from app.services.privacy import run_due_jobs

    print(json.dumps(run_due_jobs(create_db_engine()), default=str))


if __name__ == "__main__":
    main()
