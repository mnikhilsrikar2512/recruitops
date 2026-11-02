"""Liveness, readiness and metrics (Phase 6.4). Mounted at the root, not
under the API prefix, and exempt from the HTTPS redirect: they are for the
container platform and the metrics scraper inside the private network."""
from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.observability import metrics_payload

router = APIRouter(include_in_schema=False)
logger = logging.getLogger("recruitops.probes")


@router.get("/livez")
def livez() -> dict:
    """The process is up and serving. No dependencies are checked, so a
    database outage never makes the platform restart healthy containers."""
    return {"status": "ok"}


def _check_database() -> str:
    from app.api.deps import get_engine

    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        logger.warning("readiness: database check failed", exc_info=True)
        return "error"


def _check_redis() -> str:
    if not settings.redis_url:
        return "skipped"
    try:
        import redis

        redis.Redis.from_url(settings.redis_url, socket_timeout=1, socket_connect_timeout=1).ping()
        return "ok"
    except Exception:
        logger.warning("readiness: redis check failed", exc_info=True)
        return "error"


@router.get("/readyz")
def readyz() -> JSONResponse:
    """Ready to take traffic: the database and (when configured) Redis answer."""
    checks = {"database": _check_database(), "redis": _check_redis()}
    ready = all(value in ("ok", "skipped") for value in checks.values())
    return JSONResponse({"status": "ok" if ready else "unavailable", "checks": checks,
                         "version": settings.app_version}, status_code=200 if ready else 503)


@router.get("/metrics")
def metrics(request: Request) -> Response:
    if settings.metrics_token:
        supplied = request.headers.get("authorization", "")
        expected = f"Bearer {settings.metrics_token}"
        if not hmac.compare_digest(supplied.encode(), expected.encode()):
            return Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})
    body, content_type = metrics_payload()
    return Response(body, media_type=content_type)
