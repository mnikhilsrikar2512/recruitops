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
from app.main import create_application

REPO = Path(__file__).resolve().parents[2]
APP = create_application()
OPENAPI = APP.openapi()


def _route(path: str) -> APIRoute:
    return next(r for r in APP.routes if isinstance(r, APIRoute) and r.path == path and "GET" in r.methods)


def _request(path: str, **query):
    return SimpleNamespace(scope={"route": _route(path)}, query_params=query)


def test_unknown_filter_is_rejected_with_stable_code():
    with pytest.raises(ApiError) as exc:
        reject_unknown_query_params(_request("/api/v1/candidates/", page_size="10", stauts="active"))
    assert exc.value.status_code == 400
    assert exc.value.code == "UNSUPPORTED_FILTER"
    assert "stauts" in exc.value.detail


def test_known_filters_and_sort_pass():
    reject_unknown_query_params(_request("/api/v1/requisitions/", status="open", sort="-updated_at", page="2", page_size="25"))


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
    strict = {
        path for path, ops in OPENAPI["paths"].items()
        if "get" in ops and any(
            isinstance(r, APIRoute) and r.path == path and any(
                getattr(d.call, "__name__", "") == "reject_unknown_query_params" for d in r.dependant.dependencies)
            for r in APP.routes)
    }
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
