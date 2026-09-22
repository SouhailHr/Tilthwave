"""
One id per request, on the way in and on the way out.

Outermost middleware (added last in main.py): every response, including the 401/403 the auth
middlewares produce, carries X-Request-ID, and every log line written while handling the request
carries the same id (common.request_context). A client that sends its own X-Request-ID gets it
echoed, so a browser error toast, a proxy log and the API log can be matched. Pure ASGI: no
request body is read, no response is buffered.
"""

import re
import uuid

from common.request_context import reset_request_id, set_request_id

HEADER = b"x-request-id"
_ACCEPTABLE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


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

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((HEADER, request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            reset_request_id(token)
