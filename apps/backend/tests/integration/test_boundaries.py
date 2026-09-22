"""
Request ids, the error envelope, the rate-limit key behind a proxy, closed schemas, and what a
worker may not read.
"""

import logging

from starlette.requests import Request

from tests.conftest import FARM_A, zone_payload


def test_every_response_carries_a_request_id_and_an_incoming_one_is_echoed(client, auth_headers, make_farm):
    make_farm(FARM_A)
    generated = client.get("/health").headers["x-request-id"]
    assert len(generated) == 16
    echoed = client.get("/health", headers={"X-Request-ID": "trace-abc.123"}).headers["x-request-id"]
    assert echoed == "trace-abc.123"
    # not printable-safe: replaced, never reflected
    replaced = client.get("/health", headers={"X-Request-ID": "bad id\r\nX-Evil: 1"}).headers["x-request-id"]
    assert replaced != "bad id\r\nX-Evil: 1" and len(replaced) == 16


def test_error_envelope_has_a_machine_code_and_the_request_id(client, auth_headers, make_farm):
    make_farm(FARM_A)
    response = client.get("/zones/999999", headers=auth_headers())
    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "not_found"
    assert body["request_id"] == response.headers["x-request-id"]

    response = client.get("/zones/", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401
    assert response.json()["error_code"] == "unauthenticated"
    assert response.json()["request_id"] == response.headers["x-request-id"]

    response = client.get("/users/", headers=auth_headers(username="w", role="worker"))
    assert response.status_code == 403
    assert response.json()["error_code"] == "forbidden"


def test_log_records_carry_the_current_request_id_or_a_dash():
    from common.request_context import RequestIdFilter, reset_request_id, set_request_id

    record = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", None, None)
    RequestIdFilter().filter(record)
    assert record.request_id == "-"  # outside a request: streamer, flow runner, scripts
    token = set_request_id("abc123def4567890")
    try:
        RequestIdFilter().filter(record)
        assert record.request_id == "abc123def4567890"
    finally:
        reset_request_id(token)


def _request(peer: str, forwarded: str | None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers, "client": (peer, 1234)})


def test_rate_limit_key_is_the_rightmost_untrusted_forwarded_hop(monkeypatch):
    from config.settings import settings
    from interfaces.api.helpers.rate_limit import client_ip

    monkeypatch.setattr(settings.API, "TRUSTED_PROXIES", ["10.0.0.1", "10.0.0.2"])
    # a client that prepends addresses cannot pick its own bucket
    assert client_ip(_request("10.0.0.1", "6.6.6.6, 203.0.113.9, 10.0.0.2")) == "203.0.113.9"
    assert client_ip(_request("10.0.0.1", "203.0.113.9")) == "203.0.113.9"
    # the peer is not a proxy we trust: its header is ignored
    assert client_ip(_request("198.51.100.4", "6.6.6.6")) == "198.51.100.4"
    # every hop trusted: the leftmost is the best available guess
    assert client_ip(_request("10.0.0.1", "10.0.0.2")) == "10.0.0.2"
    assert client_ip(_request("10.0.0.1", None)) == "10.0.0.1"


def test_unknown_fields_are_rejected_at_every_boundary(client, auth_headers, make_farm):
    make_farm(FARM_A)
    assert client.post("/auth/login", json={"username": "x", "password": "y", "admin": True}).status_code == 422
    assert client.post("/auth/password/forgot", json={"identifier": "x", "extra": 1}).status_code == 422
    body = {**zone_payload(), "is_superuser": True}
    assert client.post("/zones/", json=body, headers=auth_headers()).status_code == 422


def test_workers_and_engineers_cannot_read_the_staff_list(client, auth_headers, make_farm):
    make_farm(FARM_A)
    for role in ("worker", "engineer"):
        assert client.get("/users/", headers=auth_headers(username=role, role=role)).status_code == 403
        assert client.get("/account/profile", headers=auth_headers(username=role, role=role)).status_code == 200
    assert client.get("/users/", headers=auth_headers(username="boss", role="owner")).status_code == 200


def test_unconfigured_mailer_never_logs_the_reset_link_on_a_tls_deployment(monkeypatch, caplog):
    from config.settings import settings
    from infrastructure.mail import Mailer

    class NoSmtp:
        HOST = None

    mailer = Mailer(NoSmtp())
    link = "https://example.com/reset-password?token=SECRET-TOKEN"

    monkeypatch.setattr(settings.API, "COOKIE_SECURE", False)
    with caplog.at_level(logging.WARNING, logger="infrastructure.mail"):
        mailer.send(to="a@b.c", subject="Reset", body=f"open {link}")
    assert "SECRET-TOKEN" in caplog.text  # local stack: the link is the only way to finish the flow

    caplog.clear()
    monkeypatch.setattr(settings.API, "COOKIE_SECURE", True)
    with caplog.at_level(logging.ERROR, logger="infrastructure.mail"):
        mailer.send(to="a@b.c", subject="Reset", body=f"open {link}")
    assert "SECRET-TOKEN" not in caplog.text and "NOT sent" in caplog.text
