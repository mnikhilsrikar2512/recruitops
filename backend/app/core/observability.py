"""Observability (Phase 6.4): request ids, structured logs, metrics, probes,
error tracking.

* Every request gets an id: a well-formed incoming ``X-Request-ID`` (from
  the load balancer) is kept, otherwise a new one is made. It is echoed in
  the response header, put in error bodies, and stamped on every log line
  written while the request runs, along with the signed-in user and
  company once authentication has resolved them.
* ``LOG_FORMAT=json`` (default in staging/production) writes one JSON
  object per line to stdout, which every log collector understands.
* One access-log line per request: method, route template, status,
  duration. Never the query string, which can carry one-time tokens.
* ``/metrics`` (Prometheus text format) counts requests and latency per
  route template and status class. Set ``METRICS_TOKEN`` to require
  ``Authorization: Bearer <token>``; staging/production require it.
* ``/livez`` (process is up) and ``/readyz`` (database and Redis answer)
  sit outside the API prefix and the HTTPS redirect, so container
  platforms can probe over plain HTTP inside the network.
* ``SENTRY_DSN`` turns on error tracking (any Sentry-compatible service:
  Sentry, GlitchTip). No request bodies, cookies or personal data are sent.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)
tenant_id_var: ContextVar[int | None] = ContextVar("tenant_id", default=None)
# One mutable dict per request. FastAPI runs sync dependencies and endpoints
# in worker threads with a *copy* of the context, so a ContextVar.set() made
# there never reaches the middleware; mutating this shared dict does.
_identity_var: ContextVar[dict | None] = ContextVar("identity", default=None)

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
PROBE_PATHS = ("/livez", "/readyz")
UNMATCHED_ROUTE = "<unmatched>"

access_logger = logging.getLogger("recruitops.access")


def current_request_id() -> str | None:
    return request_id_var.get()


def bind_identity(user_id: int | None, tenant_id: int | None) -> None:
    """Called once authentication resolves the caller."""
    user_id_var.set(user_id)
    tenant_id_var.set(tenant_id)
    identity = _identity_var.get()
    if identity is not None:
        identity["user_id"], identity["tenant_id"] = user_id, tenant_id


def _current_identity() -> tuple[int | None, int | None]:
    identity = _identity_var.get() or {}
    return (identity.get("user_id", user_id_var.get()), identity.get("tenant_id", tenant_id_var.get()))


# ---- logging -------------------------------------------------------------------

class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user_id, record.tenant_id = _current_identity()
        return True


_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message", "asctime", "request_id", "user_id", "tenant_id", "taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "env": settings.app_env,
        }
        for key in ("request_id", "user_id", "tenant_id"):
            value = getattr(record, key, None)
            if value is not None:
                entry[key] = value
        for key, value in vars(record).items():  # structured extras: logger.info("x", extra={...})
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s")


def log_format() -> str:
    chosen = (settings.log_format or "").strip().lower()
    if chosen in ("json", "text"):
        return chosen
    return "json" if settings.is_production else "text"


def configure_logging() -> None:
    """Idempotent: one stdout handler on the root logger; uvicorn's own
    loggers propagate to it so everything shares one format."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_recruitops", False):
            root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler._recruitops = True  # type: ignore[attr-defined]
    handler.addFilter(ContextFilter())
    handler.setFormatter(JsonFormatter() if log_format() == "json" else TextFormatter())
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    # Our access log replaces uvicorn's (which includes query strings).
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False


# ---- metrics -------------------------------------------------------------------

_metrics: dict[str, Any] | None = None


def _multiprocess_dir() -> str | None:
    """Set (PROMETHEUS_MULTIPROC_DIR) when several worker processes serve the
    API: each writes its numbers to files there and a scrape adds them up."""
    import os

    path = os.environ.get("PROMETHEUS_MULTIPROC_DIR", "")
    return path if path and os.path.isdir(path) else None


def _get_metrics() -> dict[str, Any] | None:
    global _metrics
    if _metrics is not None:
        return _metrics
    try:
        from prometheus_client import CollectorRegistry, Counter, Histogram
    except ImportError:  # optional in dev
        return None
    # In multiprocess mode values live in shared files; registering in a
    # per-process registry would only ever show this worker's share.
    registry = None if _multiprocess_dir() else CollectorRegistry(auto_describe=True)
    _metrics = {
        "registry": registry,
        "requests": Counter("recruitops_http_requests_total", "HTTP requests",
                            ["method", "route", "status_class"], registry=registry),
        "latency": Histogram("recruitops_http_request_duration_seconds", "HTTP request latency",
                             ["method", "route"], registry=registry,
                             buckets=(0.025, 0.05, 0.1, 0.2, 0.4, 0.8, 1.0, 2.0, 5.0, 10.0)),
        "emails": Counter("recruitops_emails_total", "Emails attempted", ["result"], registry=registry),
    }
    return _metrics


def count_email(sent: bool) -> None:
    m = _get_metrics()
    if m:
        m["emails"].labels("sent" if sent else "failed").inc()


def metrics_payload() -> tuple[bytes, str]:
    m = _get_metrics()
    if not m:
        return b"# prometheus_client not installed\n", "text/plain; charset=utf-8"
    from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

    if m["registry"] is None:
        from prometheus_client import multiprocess

        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry), CONTENT_TYPE_LATEST
    return generate_latest(m["registry"]), CONTENT_TYPE_LATEST


# ---- middleware ----------------------------------------------------------------

def _route_template(scope: dict) -> str:
    """The full path with matched parameters named, e.g.
    /api/v1/candidates/{candidate_id}/upload. Built from the request because
    nested routers only know their own part of the path. Unmatched requests
    (404s, scanners) collapse into one label so metrics stay small."""
    if scope.get("route") is None:
        return UNMATCHED_ROUTE
    params = scope.get("path_params") or {}
    segments = scope.get("path", "").split("/")
    remaining = {name: str(value) for name, value in params.items()}
    for index, segment in enumerate(segments):
        for name, value in list(remaining.items()):
            if segment == value:
                segments[index] = "{" + name + "}"
                del remaining[name]
                break
    return "/".join(segments) or "/"


class RequestContextMiddleware:
    """Pure ASGI (no BaseHTTPMiddleware) so it wraps streaming responses
    and adds no per-request task overhead."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = None
        for name, value in scope.get("headers", []):
            if name == b"x-request-id":
                incoming = value.decode("latin-1")
                break
        request_id = incoming if incoming and _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        tokens = (request_id_var.set(request_id), user_id_var.set(None), tenant_id_var.set(None),
                  _identity_var.set({}))
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status_holder = {"status": 500}

        async def send_with_id(message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            elapsed = time.perf_counter() - started
            path = scope.get("path", "")
            route = _route_template(scope)
            status_code = status_holder["status"]
            m = _get_metrics()
            if m and path not in PROBE_PATHS and path != "/metrics":
                m["requests"].labels(scope.get("method", ""), route, f"{status_code // 100}xx").inc()
                m["latency"].labels(scope.get("method", ""), route).observe(elapsed)
            if path not in PROBE_PATHS:
                level = logging.ERROR if status_code >= 500 else logging.INFO
                access_logger.log(level, "%s %s %s %.1fms", scope.get("method"), route, status_code, elapsed * 1000,
                                  extra={"http_method": scope.get("method"), "route": route, "status": status_code,
                                         "duration_ms": round(elapsed * 1000, 1)})
            for var, token in zip((request_id_var, user_id_var, tenant_id_var, _identity_var), tokens):
                var.reset(token)


# ---- error tracking --------------------------------------------------------------

_SCRUB_KEYS = re.compile(r"pass|secret|token|authorization|cookie|totp|code", re.I)


def _scrub(event: dict, _hint: dict) -> dict:
    request = event.get("request") or {}
    request.pop("data", None)
    request.pop("cookies", None)
    request.pop("query_string", None)
    headers = request.get("headers") or {}
    for key in list(headers):
        if _SCRUB_KEYS.search(key):
            headers[key] = "[scrubbed]"
    tags = event.setdefault("tags", {})
    if request_id_var.get():
        tags["request_id"] = request_id_var.get()
    tenant_id = _current_identity()[1]
    if tenant_id is not None:
        tags["tenant_id"] = str(tenant_id)
    event.pop("user", None)
    return event


def init_error_tracking() -> bool:
    if not settings.sentry_dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:
        logging.getLogger("recruitops").warning("SENTRY_DSN set but sentry-sdk is not installed")
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        release=settings.app_version,
        send_default_pii=False,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        before_send=_scrub,
    )
    return True
