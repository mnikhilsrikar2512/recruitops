"""Ops: set a company active — refused until every active Admin has MFA (D-09).

    cd backend && .venv/bin/python scripts/activate_company.py --slug northwind-staging
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.db.session import create_db_engine  # noqa: E402
from app.services.tenants import ActivationBlocked, activate_tenant  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    opts = ap.parse_args()
    engine = create_db_engine()
    with engine.connect() as connection:
        tenant_id = connection.execute(text("SELECT id FROM dbo.tenants WHERE slug = :s"), {"s": opts.slug}).scalar()
    if tenant_id is None:
        raise SystemExit(f"no company with slug {opts.slug!r}")
    try:
        activate_tenant(engine, int(tenant_id))
    except ActivationBlocked as blocked:
        raise SystemExit(f"✗ not activated — {blocked}") from None
    print(f"✓ {opts.slug} is active")


if __name__ == "__main__":
    main()
