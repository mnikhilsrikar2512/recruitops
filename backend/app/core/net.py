"""Client-address resolution behind a reverse proxy (Phase 3.7 hardening).

``X-Forwarded-For`` and ``X-Forwarded-Proto`` are set by whoever sends the
request, so trusting them unconditionally lets a caller forge its own
rate-limit bucket, the IP address stored in login/session audit records,
and whether the HTTPS redirect fires. We only trust the last
``TRUSTED_PROXY_COUNT`` hops of the header -- the ones our own
infrastructure appended -- and fall back to the direct TCP peer otherwise.

TRUSTED_PROXY_COUNT is 0 in development (headers are never trusted; the
direct peer is used) and must be set to the real proxy hop count -- usually
1 -- in staging/production (enforced by ``validate_settings``).
"""
from __future__ import annotations

from starlette.requests import Request

from app.core.config import settings


def client_ip(request: Request) -> str | None:
    """The caller's real IP address.

    With ``trusted_proxy_count`` trusted proxies in front of this app, each
    one appends the address it received the request from, so the entry
    added by the outermost trusted proxy -- the real client, as far as our
    own infrastructure can vouch for -- sits ``trusted_proxy_count`` places
    from the end of the list. Anything to the left of that may have been
    supplied by the client itself and is never trusted. With no trusted
    proxies configured, the header is ignored entirely.
    """
    trusted = settings.trusted_proxy_count
    if trusted > 0:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
            if len(hops) >= trusted:
                return hops[-trusted] or None
    return request.client.host if request.client else None


def is_forwarded_https(request: Request) -> bool:
    """Whether the original client connection was HTTPS.

    ``X-Forwarded-Proto`` is only trusted when a trusted proxy sits in
    front of us (it is the proxy, not the client, that is expected to set
    it); otherwise we go by the connection this process actually terminated.
    """
    if settings.trusted_proxy_count > 0:
        return request.headers.get("x-forwarded-proto", "https").strip().lower() != "http"
    return request.url.scheme == "https"
