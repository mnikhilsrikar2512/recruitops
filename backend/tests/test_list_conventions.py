"""Phase 4.9 — PRD §9.0 list and error conventions."""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.deps import reject_unknown_query_params, sort_clause
from app.core.errors import ApiError, http_exception_handler
from app.api.v1.candidates import list_candidates_endpoint
from app.api.v1.clients import list_clients_endpoint
from app.api.v1.requisitions import list_requisitions_endpoint
from app.main import create_application

REPO = Path(__file__).resolve().parents[2]
APP = create_application()
OPENAPI = APP.openapi()


def _request(endpoint, **query):
    return SimpleNamespace(scope={"endpoint": endpoint}, query_params=query)


def test_unknown_filter_is_rejected_with_stable_code():
    with pytest.raises(ApiError) as exc:
        reject_unknown_query_params(_request(list_candidates_endpoint, page_size="10", stauts="active"))
    assert exc.value.status_code == 400
    assert exc.value.code == "UNSUPPORTED_FILTER"
    assert "stauts" in exc.value.detail


def test_known_filters_and_sort_pass():
    reject_unknown_query_params(_request(list_requisitions_endpoint, status="open", sort="-updated_at", page="2", page_size="25"))
    reject_unknown_query_params(_request(list_clients_endpoint, location_id="3", include_archived="true"))


def test_sort_clause_allowlist():
    allowed = {"title": "title", "created_at": "created_at"}
    assert sort_clause(None, allowed, "updated_at DESC") == "updated_at DESC"
    assert sort_clause("-created_at,title", allowed, "x") == "created_at DESC, title ASC"
    with pytest.raises(ApiError) as exc:
        sort_clause("salary; DROP TABLE x", allowed, "x")
    assert exc.value.code == "UNSUPPORTED_SORT"


def test_error_envelope_shape():
    response = http_exception_handler(None, StarletteHTTPException(status_code=404, detail="Candidate was not found"))
    body = json.loads(response.body)
    assert body == {
        "detail": "Candidate was not found",
        "error": {"code": "NOT_FOUND", "message": "Candidate was not found", "field_errors": []},
    }


def _list_params(path: str) -> set[str]:
    operation = OPENAPI["paths"][path]["get"]
    return {p["name"] for p in operation.get("parameters", []) if p.get("in") == "query"}


def test_every_list_query_the_frontend_and_smoke_send_is_supported():
    """A filter the UI sends must exist on the API, or the list would now 400."""
    # Lists that carry the strict-filter dependency, found from the source.
    strict = set()
    for module in (REPO / "backend" / "app" / "api" / "v1").glob("*.py"):
        prefix = "/api/v1/" + {"daily_updates": "daily-updates", "workflow_actions": "workflow-actions", "portal": "portal-accounts", "master_data": "master-data"}.get(module.stem, module.stem)
        for path in re.findall(r'@router\.get\("([^"]*)", response_model=\w+, dependencies=\[Depends\(reject_unknown_query_params\)\]', module.read_text()):
            strict.add(prefix + path)
    sources = [p for p in (REPO / "frontend").rglob("*") if p.suffix in {".js", ".html"} and "tests" not in p.parts]
    sources.append(REPO / "tools" / "ci" / "live_smoke.py")
    problems = []
    for source in sources:
        text = source.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r'["`\'](/[a-z\-]+(?:/[a-z\-]+)?/?)\?([^"`\']*)', text):
            path = "/api/v1" + match.group(1).rstrip("/") + "/"
            if path not in strict:
                path = path.rstrip("/")
                if path not in strict:
                    continue
            for name in re.findall(r"(?:^|&)([a-z_]+)=", match.group(2)):
                if name not in _list_params(path):
                    problems.append(f"{source.name}: {path}?{name}")
    assert not problems, problems
