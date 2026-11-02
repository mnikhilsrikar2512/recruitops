"""Phase 6.4: request ids, structured logs, probes, metrics, error envelope."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.core import observability as obs
from app.core.config import settings
from app.main import create_application


def _client(monkeypatch, **overrides) -> TestClient:
    for key, value in overrides.items():
        monkeypatch.setattr(settings, key, value)
    return TestClient(create_application(), raise_server_exceptions=False)


def test_every_response_carries_a_request_id(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/livez")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert len(response.headers["X-Request-ID"]) >= 16


def test_a_well_formed_incoming_request_id_is_kept_and_a_bad_one_replaced(monkeypatch):
    client = _client(monkeypatch)
    assert client.get("/livez", headers={"X-Request-ID": "lb-abc12345"}).headers["X-Request-ID"] == "lb-abc12345"
    replaced = client.get("/livez", headers={"X-Request-ID": "bad id\nwith newline"}).headers["X-Request-ID"]
    assert replaced != "bad id\nwith newline" and " " not in replaced


def test_readiness_reports_failing_dependencies_with_503(monkeypatch):
    import app.api.probes as probes

    monkeypatch.setattr(probes, "_check_database", lambda: "error")
    monkeypatch.setattr(probes, "_check_redis", lambda: "skipped")
    response = _client(monkeypatch).get("/readyz")
    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "error", "redis": "skipped"}
    monkeypatch.setattr(probes, "_check_database", lambda: "ok")
    assert _client(monkeypatch).get("/readyz").status_code == 200


def test_metrics_need_the_token_when_one_is_set(monkeypatch):
    client = _client(monkeypatch, metrics_token="t" * 32)
    client.get("/livez")
    assert client.get("/metrics").status_code == 401
    ok = client.get("/metrics", headers={"Authorization": "Bearer " + "t" * 32})
    assert ok.status_code == 200 and b"recruitops_http_requests_total" in ok.content


def test_metrics_label_routes_by_template_not_raw_path(monkeypatch):
    monkeypatch.setattr(settings, "metrics_token", "")
    application = create_application()
    things = APIRouter()

    @things.get("/__things/{thing_id}")
    def read_thing(thing_id: int):
        return {"id": thing_id}

    application.include_router(things)
    client = TestClient(application)
    assert client.get("/__things/12345").status_code == 200
    body = client.get("/metrics").text
    assert 'route="/__things/{thing_id}"' in body
    assert "12345" not in body


def test_unhandled_errors_get_the_envelope_and_the_request_id(monkeypatch):
    application = create_application()
    boom = APIRouter()

    @boom.get("/__boom")
    def explode():
        raise RuntimeError("secret internals")

    application.include_router(boom)
    response = TestClient(application, raise_server_exceptions=False).get("/__boom", headers={"X-Request-ID": "req-00000001"})
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR" and body["request_id"] == "req-00000001"
    assert "secret internals" not in response.text


def test_json_log_lines_carry_request_and_identity(monkeypatch):
    record = logging.LogRecord("recruitops.test", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    tokens = (obs.request_id_var.set("rid-12345678"), obs.user_id_var.set(7), obs.tenant_id_var.set(3))
    try:
        obs.ContextFilter().filter(record)
        record.route = "/x"
        line = json.loads(obs.JsonFormatter().format(record))
    finally:
        for var, token in zip((obs.request_id_var, obs.user_id_var, obs.tenant_id_var), tokens):
            var.reset(token)
    assert line["msg"] == "hello world" and line["request_id"] == "rid-12345678"
    assert line["user_id"] == 7 and line["tenant_id"] == 3 and line["route"] == "/x"


def test_access_log_never_includes_the_query_string(monkeypatch, caplog):
    client = _client(monkeypatch)
    with caplog.at_level(logging.INFO, logger="recruitops.access"):
        client.get(f"{settings.api_prefix}/health?token=super-secret-token")
    access = [r.getMessage() for r in caplog.records if r.name == "recruitops.access"]
    assert access and all("super-secret-token" not in line for line in access)


def test_probes_skip_the_https_redirect_in_production(monkeypatch):
    from app.core import security_headers

    monkeypatch.setattr(settings, "app_env", "staging")
    monkeypatch.setattr(settings, "trusted_proxy_count", 1)
    # Build the app in dev (config gate), then flip to staging for the middleware's runtime check.
    monkeypatch.setattr(settings, "app_env", "development")
    application = create_application()
    monkeypatch.setattr(settings, "app_env", "staging")
    client = TestClient(application, raise_server_exceptions=False, base_url="http://internal")
    plain = {"X-Forwarded-Proto": "http"}
    assert client.get("/livez", headers=plain, follow_redirects=False).status_code == 200
    assert client.get(f"{settings.api_prefix}/health", headers=plain, follow_redirects=False).status_code == 308
    assert security_headers._PLAIN_HTTP_PATHS


def test_sentry_scrubber_drops_bodies_cookies_and_secrets():
    event = {"request": {"data": {"password": "x"}, "cookies": {"r": "1"}, "query_string": "token=abc",
                         "headers": {"Authorization": "Bearer x", "Accept": "json"}}, "user": {"email": "a@b"}}
    out = obs._scrub(event, {})
    assert "data" not in out["request"] and "cookies" not in out["request"] and "query_string" not in out["request"]
    assert out["request"]["headers"]["Authorization"] == "[scrubbed]" and out["request"]["headers"]["Accept"] == "json"
    assert "user" not in out


def test_route_labels_are_full_templates_even_in_nested_routers(monkeypatch):
    monkeypatch.setattr(settings, "metrics_token", "")
    application = create_application()
    inner = APIRouter()

    @inner.get("/{widget_id}/parts/{part_id}")
    def read_part(widget_id: int, part_id: int):
        return {}

    outer = APIRouter()
    outer.include_router(inner, prefix="/widgets")
    application.include_router(outer, prefix="/__nest")
    client = TestClient(application)
    client.get("/__nest/widgets/7/parts/7")
    client.get("/__nothing/here")
    body = client.get("/metrics").text
    assert 'route="/__nest/widgets/{widget_id}/parts/{part_id}"' in body
    assert 'route="<unmatched>"' in body and "/__nothing" not in body


def test_identity_bound_in_a_worker_thread_reaches_the_access_log(monkeypatch, caplog):
    application = create_application()
    from fastapi import Depends

    def fake_auth():
        obs.bind_identity(41, 9)  # runs in a threadpool, like get_current_auth_context
        return True

    who = APIRouter()

    @who.get("/__who")
    def endpoint(_=Depends(fake_auth)):
        return {}

    application.include_router(who)
    with caplog.at_level(logging.INFO, logger="recruitops.access"):
        TestClient(application).get("/__who")
    record = [r for r in caplog.records if r.name == "recruitops.access"][-1]
    obs.ContextFilter()  # the filter runs on the handler; emulate what it sees at log time
    assert getattr(record, "user_id", None) == 41 and getattr(record, "tenant_id", None) == 9


def test_metrics_add_up_across_worker_processes(tmp_path, monkeypatch):
    """With PROMETHEUS_MULTIPROC_DIR set, a scrape sums every worker's files."""
    import subprocess
    import sys
    import textwrap

    code = textwrap.dedent("""
        from app.core import observability as obs
        m = obs._get_metrics()
        m["requests"].labels("GET", "/x", "2xx").inc()
    """)
    env = {**__import__("os").environ, "PROMETHEUS_MULTIPROC_DIR": str(tmp_path)}
    for _ in range(2):  # two separate "workers"
        subprocess.run([sys.executable, "-c", code], check=True, env=env,
                       cwd=str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    monkeypatch.setattr(obs, "_metrics", None)
    body, _ = obs.metrics_payload()
    monkeypatch.setattr(obs, "_metrics", None)
    assert b'recruitops_http_requests_total{method="GET",route="/x",status_class="2xx"} 2.0' in body
