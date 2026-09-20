"""
Liveness/readiness probe: GET /health answers 200 when the process is up and the database
answers a trivial query, 503 otherwise. Unauthenticated (see EXCLUDED_PATHS) so container
healthchecks and the reverse proxy can call it.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette import status

from config.settings import settings
from infrastructure.repositories.base import BaseDBRepo

router = APIRouter(prefix="/health", tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("")
@router.get("/", include_in_schema=False)
def health():
    try:
        with BaseDBRepo.get_engine(settings.DATABASE.URI).connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as e:  # any driver error means "not ready"
        logger.warning("Health check failed: %s", e)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "degraded", "database": "unreachable"}
        )
    return {"status": "ok", "database": "ok"}
