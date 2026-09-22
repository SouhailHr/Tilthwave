"""
Session cookies for the browser client.

The web app authenticates with an httpOnly cookie holding the JWT: JavaScript, and therefore any
XSS payload, cannot read it, which is the whole reason the token no longer lives in localStorage.
Because the browser then attaches it to every request on its own, a state-changing request also
has to prove it came from our own page: a second, readable cookie carries a random CSRF token
that must be echoed back in the X-CSRF-Token header. Only same-origin JavaScript can read that
cookie, and a cross-site page cannot set a custom header without a CORS grant we do not give,
so a forged request has the session cookie but never the header.

API clients (the simulator, curl, Burp) keep sending Authorization: Bearer. A cross-site page
cannot set that header either, so header-authenticated requests are never CSRF-checked.
"""

import hmac
import secrets

from starlette.requests import Request
from starlette.responses import Response

from config.settings import settings

ACCESS_COOKIE = "tw_access"
CSRF_COOKIE = "tw_csrf"
CSRF_HEADER = "X-CSRF-Token"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _attributes() -> dict:
    # SameSite=Lax: the web app (:3000) and the API (:8080) are different origins but the same
    # site, so the cookie still flows on our own requests while cross-site POSTs never carry it.
    return {
        "path": "/",
        "domain": settings.API.COOKIE_DOMAIN,
        "secure": settings.API.COOKIE_SECURE,
        "samesite": "lax",
    }


def set_session_cookies(response: Response, token: str, csrf_token: str) -> None:
    max_age = settings.API.ACCESS_TOKEN_EXPIRE * 60  # same lifetime as the token inside it
    response.set_cookie(ACCESS_COOKIE, token, max_age=max_age, httponly=True, **_attributes())
    response.set_cookie(CSRF_COOKIE, csrf_token, max_age=max_age, httponly=False, **_attributes())


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, httponly=True, **_attributes())
    response.delete_cookie(CSRF_COOKIE, httponly=False, **_attributes())


def csrf_ok(request: Request) -> bool:
    """The X-CSRF-Token header matches the CSRF cookie (constant-time)."""
    header = request.headers.get(CSRF_HEADER)
    cookie = request.cookies.get(CSRF_COOKIE)
    return bool(header and cookie and hmac.compare_digest(header, cookie))
