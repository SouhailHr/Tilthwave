import logging

from jose import jwt, JWTError
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

import common.constants as global_constants
from config.settings import settings

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
        'GET': 'read',
        'HEAD': 'read',
        'OPTIONS': 'read',
        'POST': 'write',
        'PUT': 'update',
        'PATCH': 'update',
        'DELETE': 'delete',
    }
    # Unknown/unmapped methods must not silently fall through to 'read'
    # (that let PATCH updates pass a read-only role gate); deny by default.
    return method_permission_mapping.get(method.upper(), 'deny')


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


class RBACMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Path of the current request
        path = request.url.path.strip('/')
        resource = path.split('/')[0]
        # Skip permission checks for excluded paths
        if any(resource.startswith(excluded_path) for excluded_path in global_constants.EXCLUDED_PATHS):
            return await call_next(request)

        # Proceed with authorization if the path is not excluded
        authorization: str = request.headers.get('Authorization')

        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]  # Strip "Bearer " from the start

        if not token:
            return Response(content="Authorization token missing", status_code=status.HTTP_403_FORBIDDEN)

        try:
            payload = jwt.decode(token, settings.API.SECRET_KEY, algorithms=[settings.API.ALGORITHM])
            user_role = payload.get("role")

        except JWTError as e:
            return Response(content=f"Token validation error: {str(e)}", status_code=status.HTTP_403_FORBIDDEN)

        request_method = request.method.upper()

        action = translate_method_to_action(request_method)

        if not has_permission(user_role, resource, action):
            return Response(content="Insufficient permissions", status_code=status.HTTP_403_FORBIDDEN)

        return await call_next(request)
