import logging

from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

import common.constants as global_constants
from interfaces.api.helpers.auth import CLAIMS_STATE_KEY
from interfaces.api.helpers.cookies import UNSAFE_METHODS, csrf_ok
from interfaces.api.helpers.tenant import AUTH_VIA_STATE_KEY, TOKEN_INVALID_STATE_KEY

logger = logging.getLogger(__name__)


# Define role-based access control (RBAC) structure


def translate_method_to_action(method: str) -> str:
    """
    The function is designed to map HTTP methods to corresponding
    permissions for resource access control.
    @param method: a string representing an HTTP method.
    @return: HTTP method if not found it returns by default "read"
    """
    # A Mapper for HTTP methods
    method_permission_mapping = {
        "GET": "read",
        "HEAD": "read",
        "OPTIONS": "read",
        "POST": "write",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }
    # Unknown/unmapped methods must not silently fall through to 'read'
    # (that let PATCH updates pass a read-only role gate); deny by default.
    return method_permission_mapping.get(method.upper(), "deny")


def has_permission(user_role, resource_name, required_permission):
    """
    this method Checks if the specified user role has the required permission for a given resource.
    @param user_role: The role of the user.
    @param resource_name: The name of the resource.
    @param required_permission: The permission required to access the resource.
    @return: True if the permission is granted, False otherwise.
    """
    if user_role in global_constants.RESOURCES_FOR_ROLES:
        if resource_name in global_constants.RESOURCES_FOR_ROLES[user_role]:
            has_perm = required_permission in global_constants.RESOURCES_FOR_ROLES[user_role][resource_name]
            if not has_perm:
                logger.debug(f"Access denied: {user_role} lacks permission {required_permission} on {resource_name}")
            return has_perm
        else:
            logger.debug(f"Access denied: Resource {resource_name} not configured for role {user_role}")
    else:
        logger.debug(f"Access denied: Role {user_role} not found")
    return False


def _unauthorized(detail: str) -> Response:
    """401 with the JSON error envelope the web client expects and the RFC 6750 challenge header."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": detail}, headers={"WWW-Authenticate": "Bearer"}
    )


class RBACMiddleware(BaseHTTPMiddleware):
    """
    Coarse access control: <role> x <HTTP method> x <first path segment>, driven by
    RESOURCES_FOR_ROLES. Relies on TenantContextMiddleware (outermost) having decoded the
    token once into request.state.

    401 = no usable identity (missing, expired or tampered token); 403 = identity known,
    action not allowed. The web client redirects to login only on 401.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Path of the current request
        path = request.url.path.strip("/")
        resource = path.split("/")[0]
        # A cookie is attached by the browser on its own, so a state-changing request must also
        # carry the CSRF header only our own page can produce (see helpers/cookies.py). A bearer
        # header cannot be forged cross-site, so header-authenticated requests skip this. It runs
        # BEFORE the public-path exemption on purpose: /auth/logout, /auth/password/* are POSTs a
        # signed-in browser can reach, and they must be just as unforgeable as everything else.
        # Login from a browser with no session (or an expired one) has no cookie credential, so
        # it is never blocked by this.
        if (
            getattr(request.state, AUTH_VIA_STATE_KEY, None) == "cookie"
            and request.method.upper() in UNSAFE_METHODS
            and not csrf_ok(request)
        ):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN, content={"detail": "CSRF token missing or invalid"}
            )

        # Skip permission checks for the public resources (exact match: /healthz is not /health)
        if resource in global_constants.EXCLUDED_PATHS:
            return await call_next(request)

        if getattr(request.state, TOKEN_INVALID_STATE_KEY, False):
            return _unauthorized("Invalid or expired token")
        claims = getattr(request.state, CLAIMS_STATE_KEY, None)
        if claims is None:
            return _unauthorized("Not authenticated")

        action = translate_method_to_action(request.method)
        if not has_permission(claims.get("role"), resource, action):
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Insufficient permissions"})

        return await call_next(request)
