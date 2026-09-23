"""
GET /metrics: the process's Prometheus registry (common/metrics.py).

The API is reachable through the public proxy, so the endpoint is off until API_METRICS_TOKEN
is set (404 meanwhile) and then answers only a request carrying it as a bearer token (401
otherwise): Prometheus sends one with `authorization: credentials: <token>` in its scrape
config. The streamer and flow runner expose theirs on ports that stay inside the compose network.
"""

import hmac

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from starlette import status

from common.metrics import render
from config.settings import settings
from interfaces.api.helpers.errors import error_body

router = APIRouter(prefix="/metrics", tags=["Health"])


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def metrics(request: Request):
    token = settings.API.METRICS_TOKEN
    if not token:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    presented = request.headers.get("authorization", "").removeprefix("Bearer ")
    if not presented or not hmac.compare_digest(presented, token):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=error_body("Metrics token missing or invalid", "unauthenticated"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    body, content_type = render()
    return Response(content=body, media_type=content_type)
