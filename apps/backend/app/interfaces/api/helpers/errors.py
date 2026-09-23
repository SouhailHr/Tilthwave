"""
Error translation: one place that maps domain exceptions to HTTP responses.

Endpoints raise (or let propagate) domain exceptions and never build 4xx/5xx bodies
themselves. Internal messages (SQL, stack traces) stay in the logs; clients get the envelope
{"detail": <human message>, "error_code": <stable machine code>, "request_id": <id>}: the
message is for people, the code is what a client branches on, the id is what to quote when
asking about it (the same id is on every log line of that request). A request-validation
failure adds "fields": {<field>: [<message>, ...]} so a form can mark what to fix; there is
one 422 shape, whether the schema or a use case rejected the body.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from adapters.exceptions import AdaptorException
from common.exceptions import BrokerError, ConflictError, InvalidFilterError, NotFoundError
from common.request_context import current_request_id
from core.use_cases.exceptions import UseCaseException
from infrastructure.exceptions import DBReposException

logger = logging.getLogger(__name__)

# Exceptions whose message is safe to show to the client: status code and error code.
CLIENT_FACING = {
    NotFoundError: (status.HTTP_404_NOT_FOUND, "not_found"),
    ConflictError: (status.HTTP_409_CONFLICT, "conflict"),
    InvalidFilterError: (status.HTTP_400_BAD_REQUEST, "invalid_filter"),
    AdaptorException: (status.HTTP_422_UNPROCESSABLE_CONTENT, "unprocessable"),
    UseCaseException: (status.HTTP_422_UNPROCESSABLE_CONTENT, "unprocessable"),
    BrokerError: (status.HTTP_503_SERVICE_UNAVAILABLE, "broker_unavailable"),
}


def error_body(detail: str, error_code: str) -> dict:
    """The error envelope. Middlewares that answer before the endpoint use it too."""
    return {"detail": detail, "error_code": error_code, "request_id": current_request_id()}


def _error_response(status_code: int, detail: str, error_code: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error_body(detail, error_code))


# Codes for the HTTPExceptions the endpoints and dependencies raise themselves.
HTTP_STATUS_CODES = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthenticated",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_429_TOO_MANY_REQUESTS: "rate_limited",
}


def register_exception_handlers(app: FastAPI) -> None:
    for exception_class, (status_code, error_code) in CLIENT_FACING.items():
        app.add_exception_handler(exception_class, _client_facing_handler(status_code, error_code))
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(DBReposException, _database_error_handler)
    # Anything else is answered by RequestIdMiddleware (see its docstring): an app-level Exception
    # handler would run outside it and lose the request id.


async def _http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """HTTPException keeps its status and headers (WWW-Authenticate, Retry-After) and gets the envelope."""
    code = HTTP_STATUS_CODES.get(exc.status_code, "http_error")
    return JSONResponse(status_code=exc.status_code, content=error_body(str(exc.detail), code), headers=exc.headers)


async def _validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    fields: dict[str, list[str]] = {}
    for error in exc.errors():
        loc = [str(part) for part in error.get("loc", ()) if part not in ("body", "query", "path")]
        fields.setdefault(".".join(loc) or "_", []).append(error.get("msg", "invalid"))
    first_field, first_messages = next(iter(fields.items()))
    detail = f"{first_field}: {first_messages[0]}" if first_field != "_" else first_messages[0]
    body = {**error_body(detail, "validation_error"), "fields": fields}
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=body)


def _client_facing_handler(status_code: int, error_code: str):
    async def handler(_request: Request, exc: Exception) -> JSONResponse:
        return _error_response(status_code, getattr(exc, "message", None) or str(exc), error_code)

    return handler


async def _database_error_handler(request: Request, exc: DBReposException) -> JSONResponse:
    """
    503, not 500: the application is fine, its database is not. Monitors and the proxy read 500
    as an application bug; 503 with Retry-After says "try again shortly", which is the truth
    (pool_pre_ping reconnects on its own once the database is back).
    """
    logger.error("Database error on %s %s: %s", request.method, request.url.path, exc, exc_info=exc)
    response = _error_response(status.HTTP_503_SERVICE_UNAVAILABLE, "Database unavailable", "database_unavailable")
    response.headers["Retry-After"] = "5"
    return response
