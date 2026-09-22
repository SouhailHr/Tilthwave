from fastapi import APIRouter, Depends, FastAPI
from fastapi_pagination import add_pagination
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from common.logging import configure_logging
from config.settings import settings
from interfaces.api.endpoints import (
    account,
    auth,
    dashboard,
    farm,
    health,
    irrigation_task,
    sensor,
    sensor_record,
    tree,
    users,
    water_source,
    water_switcher,
    zone,
    zone_sensors,
)
from interfaces.api.helpers.auth import require_credential
from interfaces.api.helpers.errors import register_exception_handlers
from interfaces.api.helpers.permission import RBACMiddleware
from interfaces.api.helpers.tenant import TenantContextMiddleware

configure_logging(settings.LOG_LEVEL)

# Interactive docs only when API_DOCS_ENABLED=true: they map the whole attack surface.
# redirect_slashes=False: a path with the wrong trailing slash is a 404, not a 307. The redirect
# ran the whole middleware chain twice and, behind a proxy not in FORWARDED_ALLOW_IPS, sent the
# browser to an http:// Location where the Secure session cookie is not sent. Collections end
# with a slash (/zones/), items do not (/zones/1); clients are expected to get that right.
app = FastAPI(
    title="Tilthwave API",
    debug=False,
    redirect_slashes=False,
    docs_url="/docs" if settings.API.DOCS_ENABLED else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.API.DOCS_ENABLED else None,
)
register_exception_handlers(app)

# Middleware order (innermost first): RBAC authorizes, CORS answers preflights, the tenant
# middleware is added last -> outermost, so the JWT is decoded once and the ContextVar is set
# before any task boundary.
app.add_middleware(RBACMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.API.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)
app.add_middleware(TenantContextMiddleware)


@app.middleware("http")
async def strict_transport_security(request, call_next):
    """
    HSTS, keyed on the same setting as the cookie Secure flag: COOKIE_SECURE=true means the API
    is served over TLS, and then browsers must not fall back to http for the session cookie's
    host. Off (the default, and the local stack) the header would be ignored anyway.
    """
    response = await call_next(request)
    if settings.API.COOKIE_SECURE:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Authenticated resources. The dependency does not authorize (RBACMiddleware does); it documents
# the bearer requirement in OpenAPI and rejects requests carrying neither a bearer token nor the
# session cookie with a JSON 401.
api_router = APIRouter(dependencies=[Depends(require_credential)])
api_router.include_router(users.router)
api_router.include_router(farm.router)
api_router.include_router(zone.router)
api_router.include_router(zone_sensors.router)
api_router.include_router(sensor_record.router)
api_router.include_router(sensor.router)
api_router.include_router(water_source.router)
api_router.include_router(water_switcher.router)
api_router.include_router(tree.router)
api_router.include_router(irrigation_task.router)
api_router.include_router(dashboard.router)
api_router.include_router(account.router)

# Public routes
app.include_router(auth.router)
app.include_router(health.router)

app.include_router(api_router)

add_pagination(app)  # add pagination to app
