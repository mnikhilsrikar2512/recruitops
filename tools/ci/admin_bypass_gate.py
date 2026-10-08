#!/usr/bin/env python3
"""CI gate: no NEW role-code admin bypasses in the backend (plan 2.6).

Data scoping must go through backend/app/services/scope.py. Since Phase 2.5 no
route or data check depends on the role code: admins pass by grant (D-03
template, scope.company). The only remaining uses are listed in ALLOWED;
the gate fails if any file gains one.

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
    "services/users.py": 4,    # last-admin-per-company protection (role identity, not a bypass)
    "services/scope.py": 1,    # is_company_wide() fallback for hand-built contexts only
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
    print(f"✓ admin bypass gate: no role-code bypasses ({sum(ALLOWED.values())} identity checks allowed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
