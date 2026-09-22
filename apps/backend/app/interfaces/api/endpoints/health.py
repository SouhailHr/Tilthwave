"""
Two probes, unauthenticated (see permission.EXCLUDED_PATHS) so container healthchecks and the
proxy can call them:

- GET /health        liveness: the process is up and serving. Never looks at a dependency, so a
                     database outage does not get the API restarted for a problem a restart
                     cannot fix. This is the container healthcheck.
- GET /health/ready  readiness: the database answers a trivial query, 503 otherwise. For the
                     proxy, external monitoring, and the web's own /api/health/ready.
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
def live():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    try:
        with BaseDBRepo.get_engine(settings.DATABASE.URI).connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as e:  # any driver error means "not ready"
        logger.warning("Readiness check failed: %s", e)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "degraded", "database": "unreachable"}
        )
    return {"status": "ok", "database": "ok"}
