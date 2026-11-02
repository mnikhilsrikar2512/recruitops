"""Every permission an API route checks must be in the catalog the deploy
seeds; otherwise no role can ever be granted it (Phase 6.2)."""
from __future__ import annotations

import re
from pathlib import Path

from app.core.permission_catalog import PERMISSIONS, catalog
from app.core.rbac import ADMIN_PERMISSION_CODES

APP = Path(__file__).resolve().parent.parent / "app"
_CHECK = re.compile(r"(require_permissions|require_any_permission\w*|caller_has_permission|_has_permission|has_permission)\(([^)]*)\)")
_CODE = re.compile(r"\"([a-z_]+(?:\.[a-z_]+)+)\"")


def _codes_checked_by_the_app() -> set[str]:
    found: set[str] = set()
    for path in APP.rglob("*.py"):
        for match in _CHECK.finditer(path.read_text(encoding="utf-8")):
            found |= set(_CODE.findall(match.group(2)))
    return found


def test_every_checked_code_is_in_the_catalog():
    checked = _codes_checked_by_the_app()
    assert len(checked) > 50  # the scan is actually finding the routes
    missing = checked - {code for code, _m, _a in catalog()}
    assert not missing, f"add these to app/core/permission_catalog.py: {sorted(missing)}"


def test_catalog_has_no_duplicates_and_includes_admin_codes():
    codes = [code for code, _m, _a in PERMISSIONS]
    assert len(codes) == len(set(codes))
    assert set(ADMIN_PERMISSION_CODES) <= {code for code, _m, _a in catalog()}


def test_reference_seed_grants_admin_exactly_its_codes():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "seed_reference_data", APP.parent / "scripts" / "seed_reference_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Cursor:
        def __init__(self):
            self.statements = []

        def execute(self, sql, *params):
            self.statements.append((sql, params))
            self._sql = sql
            return self

        def fetchone(self):
            if "role_permissions WHERE role_id" in self._sql:
                return (len(set(ADMIN_PERMISSION_CODES)),)
            if "FROM dbo.roles" in self._sql:
                return (1,)
            return (0,)

    cursor = Cursor()
    counts = module.seed_reference_data(cursor)
    assert counts["admin_grants"] == len(set(ADMIN_PERMISSION_CODES))
    deletes = [p for s, p in cursor.statements if s.startswith("DELETE rp")]
    assert deletes and set(deletes[0][1:]) == set(ADMIN_PERMISSION_CODES)
    assert not any("dbo.users" in s or "dbo.tenants" in s for s, _p in cursor.statements)  # never creates people
