"""
One id per request, on the way in and on the way out.

Outermost middleware (added last in main.py): every response, including the 401/403 the auth
middlewares produce, carries X-Request-ID, and every log line written while handling the request
carries the same id (common.request_context). A client that sends its own X-Request-ID gets it
echoed, so a browser error toast, a proxy log and the API log can be matched. Pure ASGI: no
request body is read, no response is buffered.

Unhandled exceptions are answered here too, not by an `Exception` handler on the app: Starlette
runs that handler on its own outermost middleware, outside this one, after the ContextVar is
reset and past send_with_id, so the 500 would carry no id in its header, body or log line.
"""

import logging
import re
import uuid

from starlette import status
from starlette.responses import JSONResponse

from common.request_context import reset_request_id, set_request_id
from interfaces.api.helpers.errors import error_body

HEADER = b"x-request-id"
_ACCEPTABLE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
logger = logging.getLogger(__name__)


def _incoming_id(scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == HEADER:
            candidate = value.decode("latin-1")
            return candidate if _ACCEPTABLE.match(candidate) else None
    return None


class RequestIdMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = _incoming_id(scope) or uuid.uuid4().hex[:16]
        token = set_request_id(request_id)
        response_started = False

        async def send_with_id(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = list(message.get("headers", []))
                headers.append((HEADER, request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            logger.error("Unhandled error on %s %s", scope.get("method"), scope.get("path"), exc_info=True)
            if response_started:
                raise  # too late to answer; the server closes the connection
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_body("Internal server error", "internal_error"),
            )
            await response(scope, receive, send_with_id)
        finally:
            reset_request_id(token)
