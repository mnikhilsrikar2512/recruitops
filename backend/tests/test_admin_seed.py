"""Phase 2.5/2.6: no role-code bypass; the Admin template is the control plane (D-03)."""
import re
from pathlib import Path
from types import SimpleNamespace

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.api import deps
from app.core.rbac import ADMIN_PERMISSION_CODES, COMPANY_SCOPE_CODE
from app.services import scope
from app.services.auth import AuthContext

MIGRATION = Path(__file__).resolve().parents[2] / "scripts" / "011_admin_seed.sql"

EXECUTION_CODES = {
    "candidate.read", "candidate.create", "pipeline.read.summary", "pipeline.stage.move",
    "requisition.read", "requisition.create", "client.read", "client.create",
    "offer.create", "interview.create", "daily_update.create_main", "dashboard.read_my_work",
}


def test_migration_and_code_agree_on_the_admin_template() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    block = sql.split("INSERT INTO #admin_codes", 1)[1].split(";", 1)[0]
    in_sql = set(re.findall(r"\(N'([^']+)',", block))
    assert in_sql == set(ADMIN_PERMISSION_CODES)


def test_admin_template_is_control_plane_only() -> None:
    assert COMPANY_SCOPE_CODE in ADMIN_PERMISSION_CODES
    assert not (EXECUTION_CODES & set(ADMIN_PERMISSION_CODES))


def _ctx(role_code: str) -> AuthContext:
    return AuthContext(session_id=1, session_token_hash="t", user=SimpleNamespace(id=1, role_code=role_code, location_id=1))


def test_admin_role_code_no_longer_bypasses_permission_checks(monkeypatch) -> None:
    app = FastAPI()

    @app.get("/guarded")
    def guarded(_auth: object = Depends(deps.require_permissions("candidate.read"))) -> dict[str, str]:
        return {"ok": "yes"}

    real_engine = create_engine("sqlite://")  # a real Engine: the unit-test stub shim does not apply
    app.dependency_overrides[deps.get_current_auth_context] = lambda: _ctx("admin")
    app.dependency_overrides[deps.get_engine] = lambda: real_engine
    monkeypatch.setattr(deps, "list_resolved_permissions", lambda engine, user_id: list(ADMIN_PERMISSION_CODES))
    assert TestClient(app).get("/guarded").status_code == 403

    monkeypatch.setattr(deps, "list_resolved_permissions", lambda engine, user_id: ["candidate.read"])
    deps.invalidate_permission_cache()
    assert TestClient(app).get("/guarded").status_code == 200


def test_company_wide_reach_follows_the_grant_flag() -> None:
    admin_without_grant = _ctx("admin")
    admin_without_grant.company_wide = False
    assert scope.is_company_wide(admin_without_grant) is False

    manager_with_grant = _ctx("manager")
    manager_with_grant.company_wide = True
    assert scope.is_company_wide(manager_with_grant) is True
