"""
HTTP client for the farm-watch-commander API.

Used by the mocker to discover zones and their sensors at startup instead
of relying on a hardcoded mapping. Authenticates via /auth/login and reads
paginated /zone-sensors/ and /sensors/ endpoints.
"""
import logging

import requests

from config.settings import settings

logger = logging.getLogger(__name__)


class FarmApiClient:
    DEFAULT_PAGE_SIZE = 100
    REQUEST_TIMEOUT = 10

    def __init__(self):
        self.base_url = settings.API.BASE_URL.rstrip("/")
        self.session = requests.Session()

    def login(self):
        url = f"{self.base_url}/auth/login"
        resp = self.session.post(
            url,
            json={
                "username": settings.API.USERNAME,
                "password": settings.API.PASSWORD,
            },
            timeout=self.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        token = resp.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        logger.info("Authenticated against %s", self.base_url)

    def _get_paginated(self, path):
        items = []
        page = 1
        while True:
            resp = self.session.get(
                f"{self.base_url}{path}",
                params={"page": page, "size": self.DEFAULT_PAGE_SIZE},
                timeout=self.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            payload = resp.json()
            items.extend(payload.get("items", []))
            total_pages = payload.get("pages") or 0
            if page >= total_pages:
                break
            page += 1
        return items

    def get_zone_sensors(self):
        return self._get_paginated("/zone-sensors/")

    def get_sensors(self):
        return self._get_paginated("/sensors/")