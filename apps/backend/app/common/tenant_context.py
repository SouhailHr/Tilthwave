"""Request-scoped tenant context.

Set by the HTTP layer (TenantContextMiddleware) from the caller's JWT and read
by the repository layer to scope every query to the caller's farm. Lives in the
`common` layer so both `interfaces` and `infrastructure` can import it without a
layering violation. A ContextVar is used so no identity has to be threaded
through every function signature; it is None for non-HTTP callers (flow runner,
streamer, scripts), which therefore run unscoped by design.
"""

import contextvars
from contextlib import contextmanager
from typing import TypedDict


class TenantContext(TypedDict, total=False):
    user_id: int | None
    username: str | None
    farm_name: str | None
    role: str | None
    is_superuser: bool


_current_tenant: contextvars.ContextVar[TenantContext | None] = contextvars.ContextVar("current_tenant", default=None)


def set_tenant(ctx: TenantContext | None):
    return _current_tenant.set(ctx)


def reset_tenant(token) -> None:
    _current_tenant.reset(token)


def get_current_tenant() -> TenantContext | None:
    return _current_tenant.get()


@contextmanager
def without_tenant():
    """
    Run the block with no tenant bound, so the repositories are unscoped for its duration.

    For a caller acting on its OWN user row, identified by the verified user_id from the
    session: the farm filter has nothing to add there. Never use it to read anything the caller
    did not already own.
    """
    token = set_tenant(None)
    try:
        yield
    finally:
        reset_tenant(token)
