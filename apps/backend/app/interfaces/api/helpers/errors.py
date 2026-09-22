"""
Error translation: one place that maps domain exceptions to HTTP responses.

Endpoints raise (or let propagate) domain exceptions and never build 4xx/5xx bodies
themselves. Internal messages (SQL, stack traces) stay in the logs; clients get the envelope
{"detail": <human message>, "error_code": <stable machine code>, "request_id": <id>}: the
message is for people, the code is what a client branches on, the id is what to quote when
asking about it (the same id is on every log line of that request).
"""

import logging

from fastapi import FastAPI, Request
from starlette import status
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


def register_exception_handlers(app: FastAPI) -> None:
    for exception_class, (status_code, error_code) in CLIENT_FACING.items():
        app.add_exception_handler(exception_class, _client_facing_handler(status_code, error_code))
    app.add_exception_handler(DBReposException, _database_error_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)


def _client_facing_handler(status_code: int, error_code: str):
    async def handler(_request: Request, exc: Exception) -> JSONResponse:
        return _error_response(status_code, getattr(exc, "message", None) or str(exc), error_code)

    return handler


async def _database_error_handler(request: Request, exc: DBReposException) -> JSONResponse:
    logger.error("Database error on %s %s: %s", request.method, request.url.path, exc, exc_info=exc)
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database error", "database_error")


async def _unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error", "internal_error")
