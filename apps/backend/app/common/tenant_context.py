"""Request-scoped tenant context.

Set by the HTTP layer (TenantContextMiddleware) from the caller's JWT and read
by the repository layer to scope every query to the caller's farm. Lives in the
`common` layer so both `interfaces` and `infrastructure` can import it without a
layering violation. A ContextVar is used so no identity has to be threaded
through every function signature; it is None for non-HTTP callers (flow runner,
streamer, scripts), which therefore run unscoped by design.
"""
import contextvars
from typing import Optional, TypedDict


class TenantContext(TypedDict, total=False):
    username: Optional[str]
    farm_name: Optional[str]
    role: Optional[str]
    is_superuser: bool


_current_tenant: contextvars.ContextVar[Optional[TenantContext]] = contextvars.ContextVar(
    "current_tenant", default=None
)


def set_tenant(ctx: Optional[TenantContext]):
    return _current_tenant.set(ctx)


def reset_tenant(token) -> None:
    _current_tenant.reset(token)


def get_current_tenant() -> Optional[TenantContext]:
    return _current_tenant.get()
