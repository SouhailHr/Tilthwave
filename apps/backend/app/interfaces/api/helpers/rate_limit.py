"""
In-process sliding-window rate limiter, used as a FastAPI dependency on /auth/login.

Scoped per client IP. The client IP is the TCP peer unless that peer is a trusted reverse proxy
(API_TRUSTED_PROXIES), in which case the first X-Forwarded-For hop is used: a header from an
untrusted peer is never believed, so it cannot be rotated to escape the limit.

Counters are per process: with N uvicorn workers the effective limit is N x the configured value.
Good enough for the current single-host deployment; a multi-replica deployment should limit at the
reverse proxy or move the counters to Redis.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request
from starlette import status

from config.settings import settings

WINDOW_SECONDS = 60


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int = WINDOW_SECONDS):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """
        Record one hit for `key`; raise 429 when the window already holds `limit` hits.
        """
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = int(self.window_seconds - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts, try again later",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)
            self._evict_idle(now)

    def _evict_idle(self, now: float) -> None:
        """Drop keys whose window emptied, so the table does not grow with every IP ever seen."""
        for key in [k for k, hits in self._hits.items() if not hits or now - hits[-1] > self.window_seconds]:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


login_rate_limiter = SlidingWindowRateLimiter(limit=settings.API.LOGIN_RATE_LIMIT_PER_MINUTE)


def client_ip(request: Request) -> str:
    """
    The caller's address: the TCP peer, or the first X-Forwarded-For hop when the peer is a
    trusted proxy.
    """
    peer = request.client.host if request.client else "unknown"
    if peer in settings.API.TRUSTED_PROXIES:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return peer


def limit_login_attempts(request: Request) -> None:
    login_rate_limiter.check(client_ip(request))
