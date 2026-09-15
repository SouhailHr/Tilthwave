import pytest
import requests

from sensors.api_client import FarmApiClient


class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._body


def _client_with(monkeypatch, responses):
    client = FarmApiClient()
    calls = iter(responses)

    def fake_post(*_args, **_kwargs):
        response = next(calls)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(client.session, "post", fake_post)
    monkeypatch.setattr("sensors.api_client.time.sleep", lambda _s: None)
    return client


def test_login_retries_while_the_api_starts_then_sets_the_bearer(monkeypatch):
    client = _client_with(
        monkeypatch, [requests.ConnectionError("refused"), FakeResponse(400), FakeResponse(200, {"token": "abc"})]
    )
    client.login()
    assert client.session.headers["Authorization"] == "Bearer abc"


def test_login_fails_fast_on_a_real_client_error(monkeypatch):
    client = _client_with(monkeypatch, [FakeResponse(403), FakeResponse(200, {"token": "never"})])
    with pytest.raises(requests.HTTPError):
        client.login()


def test_login_gives_up_after_max_attempts(monkeypatch):
    client = _client_with(monkeypatch, [FakeResponse(503)] * 3)
    with pytest.raises(RuntimeError):
        client.login()
