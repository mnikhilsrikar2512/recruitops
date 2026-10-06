"""Perimeter (Phase 3.8): security headers on every response, HSTS and an
HTTP→HTTPS redirect in staging/production (TLS terminates at the load
balancer, which sets X-Forwarded-Proto)."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.core.config import settings

_DOC_PATHS = ("/docs", "/redoc", "/openapi.json")
_BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if settings.is_production and request.headers.get("x-forwarded-proto", "https") == "http":
            return RedirectResponse(request.url.replace(scheme="https"), status_code=308)
        response = await call_next(request)
        for name, value in _BASE_HEADERS.items():
            response.headers.setdefault(name, value)
        if not request.url.path.startswith(_DOC_PATHS):
            response.headers.setdefault("Content-Security-Policy", _API_CSP)
        if request.url.path.startswith(settings.api_prefix):
            response.headers.setdefault("Cache-Control", "no-store")
        if settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
