"""Pure-ASGI middleware that binds the caller's tenant (farm) for the request.

Decodes the Bearer JWT once and stores {username, farm_name, role, is_superuser}
in a ContextVar the repository layer reads to enforce per-farm isolation. Being
a plain ASGI middleware (not BaseHTTPMiddleware), it sets the ContextVar in the
same context that runs the endpoint, so the value is visible to sync handlers
executed in the threadpool. Install it OUTERMOST so the value is set before any
downstream task boundary copies the context.
"""
from jose import JWTError, jwt

from common.tenant_context import reset_tenant, set_tenant
from config.settings import settings

SUPERUSER_ROLES = ("admin", "owner")


class TenantContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        ctx = None
        headers = dict(scope.get("headers") or [])
        authorization = headers.get(b"authorization", b"").decode()
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            try:
                payload = jwt.decode(
                    token, settings.API.SECRET_KEY, algorithms=[settings.API.ALGORITHM]
                )
                role = payload.get("role")
                ctx = {
                    "username": payload.get("username"),
                    "farm_name": payload.get("farm_name"),
                    "role": role,
                    "is_superuser": role in SUPERUSER_ROLES,
                }
            except JWTError:
                ctx = None
        token_ctx = set_tenant(ctx)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_tenant(token_ctx)
