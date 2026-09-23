"""
Pure-ASGI middleware counting requests and their latency per route template.

The route template (`/zones/{id}`, not `/zones/17`) is what keeps the label set bounded; it is
known only after routing, so the middleware reads it back from the scope once the app has
answered. Requests that matched no route are counted under "unmatched". Installed inside
RequestIdMiddleware, so a request the outer layers refuse (no id) is still counted.
"""

import time

from common.metrics import HTTP_LATENCY, HTTP_REQUESTS


class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status_holder = {"status": 500}

        async def send_with_status(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            route = scope.get("route")
            template = getattr(route, "path", None) or "unmatched"
            method = scope.get("method", "GET")
            HTTP_REQUESTS.labels(method, template, f"{status_holder['status'] // 100}xx").inc()
            HTTP_LATENCY.labels(method, template).observe(time.perf_counter() - started)
