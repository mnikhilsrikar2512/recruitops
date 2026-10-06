#!/usr/bin/env python3
"""CI gate: no NEW role-code admin bypasses in the backend (plan 2.6).

Data scoping must go through backend/app/services/scope.py. The sites listed
in ALLOWED are the known remaining bypasses (permission checks and
last-admin protection) that Phase 2.5 removes together with the D-03 Admin
seed; the gate fails if any file gains one, so the list can only shrink.

    python3 tools/ci/admin_bypass_gate.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "backend" / "app"
PATTERN = re.compile(r"""role_code\s*[!=]=\s*["']admin["']|role_code\s*==\s*["']admin["']""")

# file (relative to backend/app) → allowed occurrences. Shrink, never grow.
ALLOWED = {
    "api/deps.py": 2,          # require_permissions / require_any_permission  (Phase 2.5)
    "api/v1/agents.py": 1,     # agent run permission                           (Phase 2.5)
    "services/agents.py": 1,   # agent permission guard                         (Phase 2.5)
    "services/auth.py": 1,     # /auth/me scope labels                          (Phase 2.5)
    "services/users.py": 4,    # last-admin-per-company protection              (Phase 2.5)
    "services/scope.py": 1,    # THE one place: is_company_wide()
}


def main() -> int:
    failures = []
    for path in sorted(APP.rglob("*.py")):
        rel = path.relative_to(APP).as_posix()
        count = len(PATTERN.findall(path.read_text(encoding="utf-8")))
        if count > ALLOWED.get(rel, 0):
            failures.append(f"{rel}: {count} admin role checks (allowed {ALLOWED.get(rel, 0)})")
    if failures:
        print("✗ new role-code admin bypasses — scope data through app/services/scope.py instead:")
        for line in failures:
            print("   ", line)
        return 1
    print(f"✓ admin bypass gate: no new role-code checks ({sum(ALLOWED.values())} known, shrinking in Phase 2.5)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
