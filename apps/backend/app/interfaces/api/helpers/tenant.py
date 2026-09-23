"""Pure-ASGI middleware that binds the caller's tenant (farm) for the request.

Takes the credential from the Authorization header (API clients) or, failing that, from the
httpOnly session cookie (the web app), decodes it once, loads the user row and the session row
(`jti`) it names and stores {username, farm_name, role, is_superuser} in a ContextVar the repository
layer reads to enforce per-farm isolation. Role and farm come from the database, not the token, and a missing or
deactivated user is rejected: deactivating or demoting someone takes effect on their next request
instead of when their token expires. Being a plain ASGI middleware (not BaseHTTPMiddleware), it
sets the ContextVar in the same context that runs the endpoint, so the value is visible to sync
handlers executed in the threadpool. Install it OUTERMOST so the value is set before any
downstream task boundary copies the context.

The decoded claims are also stored on the request state (AuthHelper.CLAIMS_STATE_KEY), with which
channel supplied the credential (AUTH_VIA_STATE_KEY: "header" or "cookie"), so RBACMiddleware and
the endpoint dependencies reuse them instead of decoding again, and RBACMiddleware knows whether
the request needs a CSRF check.
"""

from http.cookies import CookieError, SimpleCookie

from jwt import InvalidTokenError
from starlette.concurrency import run_in_threadpool

from common import constants as global_constants
from common.tenant_context import reset_tenant, set_tenant
from interfaces.api.helpers.auth import CLAIMS_STATE_KEY, AuthHelper
from interfaces.api.helpers.cookies import ACCESS_COOKIE
from wiring import api_use_cases

# Request-state flag telling RBACMiddleware a credential was present but rejected.
TOKEN_INVALID_STATE_KEY = "auth_token_invalid"
# Request-state channel the credential came from: "header", "cookie" or None.
AUTH_VIA_STATE_KEY = "auth_via"


class TenantContextMiddleware:
    def __init__(self, app):
        self.app = app

    @staticmethod
    def _active_session(claims: dict):
        """
        (user, session) behind a decoded token, or (None, None): the user row must exist and be
        active, and the session row named by `jti` must be live and belong to that user. A token
        with a `purpose` (password reset) is never a session, however valid its signature.
        """
        user_id = claims.get("user_id")
        if user_id is None or claims.get("purpose") is not None:
            return None, None
        use_cases = api_use_cases()
        # No tenant context is set yet, so this lookup is unscoped: the row itself tells the farm.
        user = use_cases.users.get(user_id)
        if user is None or not user.is_active:
            return None, None
        session = use_cases.sessions.resolve(claims.get("jti"))
        if session is None or session.user_id != user.id:
            return None, None
        return user, session

    @staticmethod
    def _credential(headers: dict) -> tuple[str | None, str | None]:
        """(token, channel): the bearer token when the header is present, else the session cookie."""
        authorization = headers.get(b"authorization", b"").decode()
        if authorization.startswith("Bearer "):
            return authorization.removeprefix("Bearer "), "header"
        jar = SimpleCookie()
        try:
            jar.load(headers.get(b"cookie", b"").decode())
        except CookieError:
            return None, None
        morsel = jar.get(ACCESS_COOKIE)
        if morsel is not None and morsel.value:
            return morsel.value, "cookie"
        return None, None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        state = scope.setdefault("state", {})
        state[CLAIMS_STATE_KEY] = None
        state[TOKEN_INVALID_STATE_KEY] = False
        state[AUTH_VIA_STATE_KEY] = None
        ctx = None
        headers = dict(scope.get("headers") or [])
        token, via = self._credential(headers)
        if token:
            try:
                claims = AuthHelper.decode_token(token)
            except InvalidTokenError:
                state[TOKEN_INVALID_STATE_KEY] = True
            else:
                # The repositories are synchronous; keep the event loop free while the rows load.
                user, session = await run_in_threadpool(self._active_session, claims)
                if user is None:
                    state[TOKEN_INVALID_STATE_KEY] = True
                else:
                    claims = {
                        **claims,
                        "username": user.username,
                        "role": user.role,
                        "farm_name": user.farm_name,
                        "session_id": session.id,
                    }
                    state[CLAIMS_STATE_KEY] = claims
                    state[AUTH_VIA_STATE_KEY] = via
                    ctx = {
                        "username": user.username,
                        "farm_name": user.farm_name,
                        "role": user.role,
                        "is_superuser": user.role in global_constants.SUPERUSER_ROLES,
                    }
        token_ctx = set_tenant(ctx)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_tenant(token_ctx)
