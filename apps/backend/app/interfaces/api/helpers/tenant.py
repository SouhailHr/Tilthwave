"""Pure-ASGI middleware that binds the caller's tenant (farm) for the request.

Decodes the Bearer JWT once and stores {username, farm_name, role, is_superuser}
in a ContextVar the repository layer reads to enforce per-farm isolation. Being
a plain ASGI middleware (not BaseHTTPMiddleware), it sets the ContextVar in the
same context that runs the endpoint, so the value is visible to sync handlers
executed in the threadpool. Install it OUTERMOST so the value is set before any
downstream task boundary copies the context.

The decoded claims are also stored on the request state (AuthHelper.CLAIMS_STATE_KEY)
so RBACMiddleware and the endpoint dependencies reuse them instead of decoding again.
"""

from jwt import InvalidTokenError

from common import constants as global_constants
from common.tenant_context import reset_tenant, set_tenant
from interfaces.api.helpers.auth import CLAIMS_STATE_KEY, AuthHelper

# Request-state flag telling RBACMiddleware a bearer token was present but rejected.
TOKEN_INVALID_STATE_KEY = "auth_token_invalid"


class TenantContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        state = scope.setdefault("state", {})
        state[CLAIMS_STATE_KEY] = None
        state[TOKEN_INVALID_STATE_KEY] = False
        ctx = None
        headers = dict(scope.get("headers") or [])
        authorization = headers.get(b"authorization", b"").decode()
        if authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ")
            try:
                claims = AuthHelper.decode_token(token)
            except InvalidTokenError:
                state[TOKEN_INVALID_STATE_KEY] = True
            else:
                role = claims.get("role")
                state[CLAIMS_STATE_KEY] = claims
                ctx = {
                    "username": claims.get("username"),
                    "farm_name": claims.get("farm_name"),
                    "role": role,
                    "is_superuser": role in global_constants.SUPERUSER_ROLES,
                }
        token_ctx = set_tenant(ctx)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_tenant(token_ctx)
