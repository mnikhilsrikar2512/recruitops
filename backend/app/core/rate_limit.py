"""Rate limiting (Phase 3.7, PRD §10).

Fixed one-minute windows keyed by (rule, subject). Redis when REDIS_URL is set
(required in staging/production so every API instance shares the counters);
an in-process counter otherwise (dev, single process). Over the limit → 429
with Retry-After.

Defaults (PRD §10): login 5/min/IP + 10/min/account; forgot-password
5/min/IP + 3/min/account; password reset/setup 10/min/IP; refresh 30/min/IP.
"""
from __future__ import annotations

import threading
import time

from fastapi import HTTPException, Request, status

from app.core import net
from app.core.config import settings

RULES: dict[str, int] = {
    "login:ip": 5,
    "login:account": 10,
    "forgot:ip": 5,
    "forgot:account": 3,
    "password_token:ip": 10,
    "refresh:ip": 30,
    "mfa:account": 10,
    "signup:ip": 5,  # Phase 5.2: new companies per minute per IP
    "signup_verify:ip": 20,
}
WINDOW_SECONDS = 60


class _MemoryCounter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, tuple[int, int]] = {}

    def hit(self, key: str) -> int:
        window = int(time.time() // WINDOW_SECONDS)
        with self._lock:
            current_window, count = self._counts.get(key, (window, 0))
            if current_window != window:
                count = 0
            count += 1
            self._counts[key] = (window, count)
            if len(self._counts) > 50_000:  # bounded memory
                self._counts = {k: v for k, v in self._counts.items() if v[0] == window}
            return count

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


class _RedisCounter:
    def __init__(self, url: str) -> None:
        import redis  # noqa: PLC0415 — only needed when REDIS_URL is set

        self._client = redis.Redis.from_url(url, socket_timeout=1)

    def hit(self, key: str) -> int:
        window = int(time.time() // WINDOW_SECONDS)
        redis_key = f"rl:{key}:{window}"
        pipe = self._client.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, WINDOW_SECONDS + 5)
        count, _ = pipe.execute()
        return int(count)

    def reset(self) -> None:  # tests only
        pass


_memory = _MemoryCounter()
_counter = None


def _get_counter():
    global _counter
    if _counter is None:
        _counter = _RedisCounter(settings.redis_url) if settings.redis_url else _memory
    return _counter


def reset_rate_limits() -> None:
    _memory.reset()


def client_ip(request: Request) -> str:
    """The caller's real IP (see app.core.net) -- never trusted blindly
    from a client-supplied header. Falls back to "unknown" only when
    there's truly no peer to report (e.g. a fully mocked request)."""
    return net.client_ip(request) or "unknown"


def enforce(rule: str, subject: str | None) -> None:
    """Count one attempt for (rule, subject); 429 when over the limit."""
    if not settings.rate_limit_enabled or not subject:
        return
    limit = RULES[rule]
    try:
        count = _get_counter().hit(f"{rule}:{subject.lower()}")
    except Exception:  # noqa: BLE001 — a broken cache must not take sign-in down
        return
    if count > limit:
        retry_after = WINDOW_SECONDS - int(time.time()) % WINDOW_SECONDS
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait a minute and try again.",
            headers={"Retry-After": str(retry_after)},
        )
