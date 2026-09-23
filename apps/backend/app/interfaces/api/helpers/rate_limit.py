"""
In-process sliding-window rate limiters for the auth routes.

Two keys. Per client IP (limit_login_attempts, limit_password_reset_attempts) bounds what one
address can try. Per account (account_lockout) bounds what can be tried against one username from
any number of addresses: LOGIN_FAILURES_PER_ACCOUNT wrong passwords in LOGIN_FAILURE_WINDOW_MINUTES
and the account is refused with a 429 until the window slides, right password or not; a successful
login clears the count. Without it a credential-stuffing run spread over many addresses would never
hit the per-IP limit.

The per-IP key is scoped per client IP. The client IP is the TCP peer unless that peer is a trusted reverse proxy
(API_TRUSTED_PROXIES), in which case the first X-Forwarded-For hop is used: a header from an
untrusted peer is never believed, so it cannot be rotated to escape the limit.

Counters are per process: with N uvicorn workers the effective limit is N x the configured value.
Good enough for the current single-host deployment; a multi-replica deployment should limit at the
reverse proxy or move the counters to Redis.
"""

import ipaddress
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


class FailureLockout:
    """
    Sliding window over *failures* per key. `check` refuses a key with `limit` failures in the
    window (429 with Retry-After), `record` adds one, `clear` forgets the key.
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._failures = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque:
        failures = self._failures[key]
        while failures and now - failures[0] > self.window_seconds:
            failures.popleft()
        if not failures:
            del self._failures[key]
        return failures

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            failures = self._prune(key, now)
            if len(failures) >= self.limit:
                retry_after = int(self.window_seconds - (now - failures[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts, try again later",
                    headers={"Retry-After": str(retry_after)},
                )

    def record(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._failures[key].append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_rate_limiter = SlidingWindowRateLimiter(limit=settings.API.LOGIN_RATE_LIMIT_PER_MINUTE)


def is_trusted_proxy(address: str, trusted: list[str] | None = None) -> bool:
    """
    Whether `address` is one of API_TRUSTED_PROXIES. An entry may be an address (10.0.1.2), a
    network (10.0.1.0/24: a docker proxy's address changes when its container restarts, the
    network it sits on does not) or, for test clients, any other string matched exactly.
    """
    entries = settings.API.TRUSTED_PROXIES if trusted is None else trusted
    for entry in entries:
        if entry == address:
            return True
        try:
            if ipaddress.ip_address(address) in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False


def client_ip(request: Request) -> str:
    """
    The caller's address for the rate-limit key: the TCP peer, or, when the peer is a trusted
    proxy, the rightmost X-Forwarded-For hop that is not itself a trusted proxy. The leftmost hop
    is whatever the client sent; taking it let anyone behind the proxy pick a fresh bucket per
    request by prepending a random address.
    """
    peer = request.client.host if request.client else "unknown"
    if not is_trusted_proxy(peer):
        return peer
    hops = [hop.strip() for hop in request.headers.get("x-forwarded-for", "").split(",") if hop.strip()]
    for hop in reversed(hops):
        if not is_trusted_proxy(hop):
            return hop
    return hops[0] if hops else peer


def limit_login_attempts(request: Request) -> None:
    login_rate_limiter.check(client_ip(request))


# Forgot/reset-password share one window, separate from login's: a flood of reset requests must
# not lock a legitimate login out, and vice versa. Same per-IP limit.
password_reset_rate_limiter = SlidingWindowRateLimiter(limit=settings.API.LOGIN_RATE_LIMIT_PER_MINUTE)


def limit_password_reset_attempts(request: Request) -> None:
    password_reset_rate_limiter.check(client_ip(request))


account_lockout = FailureLockout(
    limit=settings.API.LOGIN_FAILURES_PER_ACCOUNT, window_seconds=settings.API.LOGIN_FAILURE_WINDOW_MINUTES * 60
)
