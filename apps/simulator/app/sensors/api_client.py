"""
HTTP client for the Tilthwave API.

Used by the sensor simulator to discover zones and their sensors at startup instead
of relying on a hardcoded mapping. Authenticates via /auth/login and reads
paginated /zone-sensors/ and /sensors/ endpoints.
"""

import logging
import time

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
        """
        Authenticate, retrying while the API is still starting (connection errors, 5xx, or the
        seeded admin not existing yet). Bad credentials (4xx) fail immediately.
        """
        url = f"{self.base_url}/auth/login"
        credentials = {"username": settings.API.USERNAME, "password": settings.API.PASSWORD}
        for attempt in range(1, settings.API.LOGIN_MAX_ATTEMPTS + 1):
            try:
                resp = self.session.post(url, json=credentials, timeout=self.REQUEST_TIMEOUT)
            except requests.RequestException as e:
                reason = str(e)
            else:
                if resp.status_code == 200:
                    token = resp.json()["token"]
                    self.session.headers.update({"Authorization": f"Bearer {token}"})
                    logger.info("Authenticated against %s", self.base_url)
                    return
                if resp.status_code != 400 and resp.status_code < 500:
                    resp.raise_for_status()  # 401/403/404...: a real client error, no point retrying
                # 400 = the seeded admin does not exist yet, or SIM_PASSWORD is wrong: the API's
                # message tells the two apart, so it goes in the log; 5xx = the API is still starting
                try:
                    detail = resp.json().get("detail", "")
                except ValueError:
                    detail = ""
                reason = f"HTTP {resp.status_code}" + (f": {detail}" if detail else "")
            logger.warning(
                "Login attempt %d/%d failed (%s); retrying in %.0fs",
                attempt,
                settings.API.LOGIN_MAX_ATTEMPTS,
                reason,
                settings.API.LOGIN_RETRY_SECONDS,
            )
            time.sleep(settings.API.LOGIN_RETRY_SECONDS)
        raise RuntimeError(f"Could not log in to {self.base_url} after {settings.API.LOGIN_MAX_ATTEMPTS} attempts")

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
