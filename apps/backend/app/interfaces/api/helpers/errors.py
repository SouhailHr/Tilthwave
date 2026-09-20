"""
Error translation: one place that maps domain exceptions to HTTP responses.

Endpoints raise (or let propagate) domain exceptions and never build 4xx/5xx bodies
themselves. Internal messages (SQL, stack traces) stay in the logs; clients get the
{"detail": ...} envelope the web client already parses.
"""

import logging

from fastapi import FastAPI, Request
from starlette import status
from starlette.responses import JSONResponse

from adapters.exceptions import AdaptorException
from common.exceptions import BrokerError, ConflictError, InvalidFilterError, NotFoundError
from core.use_cases.exceptions import UseCaseException
from infrastructure.exceptions import DBReposException

logger = logging.getLogger(__name__)

# Exceptions whose message is safe to show to the client, with their status code.
CLIENT_FACING = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    InvalidFilterError: status.HTTP_400_BAD_REQUEST,
    AdaptorException: status.HTTP_422_UNPROCESSABLE_CONTENT,
    UseCaseException: status.HTTP_422_UNPROCESSABLE_CONTENT,
    BrokerError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _error_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    for exception_class, status_code in CLIENT_FACING.items():
        app.add_exception_handler(exception_class, _client_facing_handler(status_code))
    app.add_exception_handler(DBReposException, _database_error_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)


def _client_facing_handler(status_code: int):
    async def handler(_request: Request, exc: Exception) -> JSONResponse:
        return _error_response(status_code, getattr(exc, "message", None) or str(exc))

    return handler


async def _database_error_handler(request: Request, exc: DBReposException) -> JSONResponse:
    logger.error("Database error on %s %s: %s", request.method, request.url.path, exc, exc_info=exc)
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database error")


async def _unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")
