"""
Forgot / reset password: an emailed single-use, time-limited link. The endpoints are public, so
they must not reveal which accounts exist, and a reset token must never double as a session.
"""

import logging
import re

import pytest

from infrastructure.mail import mailer
from interfaces.api.endpoints.auth import FORGOT_DETAIL, RESET_INVALID_DETAIL
from interfaces.api.helpers.auth import AuthHelper
from tests.conftest import FARM_A

PASSWORD = "Passw0rd-Test!"  # make_user's default
NEW_PASSWORD = "N3w-Passw0rd-Test!"
LINK = re.compile(r"http://localhost:3000/reset-password\?token=(\S+)")


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(mailer, "send", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


def _forgot(client, identifier):
    return client.post("/auth/password/forgot", json={"identifier": identifier})


def _token_from(outbox) -> str:
    return LINK.search(outbox[-1][2]).group(1)


def test_forgot_emails_a_reset_link_for_a_username_or_an_email(client, make_farm, make_user, outbox):
    make_farm(FARM_A)
    make_user("pat")  # email pat@example.com

    response = _forgot(client, "pat")
    assert response.status_code == 202 and response.json()["message"] == FORGOT_DETAIL
    assert len(outbox) == 1
    to, subject, body = outbox[0]
    assert to == "pat@example.com" and "Reset" in subject and LINK.search(body)

    assert _forgot(client, "pat@example.com").status_code == 202
    assert len(outbox) == 2


def test_forgot_answers_identically_and_sends_nothing_for_unknown_or_inactive(
    client, make_farm, make_user, repos, outbox
):
    make_farm(FARM_A)
    known = _forgot(client, "nobody-here")
    assert known.status_code == 202 and known.json()["message"] == FORGOT_DETAIL

    make_user("gone")
    row = repos.users.first([{"attribute": "username", "value": "gone", "condition": "eq"}])
    repos.users.update(row.id, {"is_active": False})
    assert _forgot(client, "gone").status_code == 202

    assert outbox == []


def test_reset_sets_the_new_password_and_the_link_is_single_use(client, make_farm, make_user, outbox):
    make_farm(FARM_A)
    make_user("pat")
    _forgot(client, "pat")
    token = _token_from(outbox)

    response = client.post("/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD})
    assert response.status_code == 204
    assert client.post("/auth/login", json={"username": "pat", "password": PASSWORD}).status_code == 400
    assert client.post("/auth/login", json={"username": "pat", "password": NEW_PASSWORD}).status_code == 200

    # Same link again: the password it was issued against is gone, so it no longer matches.
    again = client.post("/auth/password/reset", json={"token": token, "new_password": "Another-Passw0rd!"})
    assert again.status_code == 400 and again.json()["detail"] == RESET_INVALID_DETAIL
    assert client.post("/auth/login", json={"username": "pat", "password": NEW_PASSWORD}).status_code == 200


def test_reset_rejects_tampered_expired_and_wrong_purpose_tokens(client, make_farm, make_user, outbox, monkeypatch):
    make_farm(FARM_A)
    make_user("pat")
    _forgot(client, "pat")
    token = _token_from(outbox)

    tampered = client.post("/auth/password/reset", json={"token": token + "x", "new_password": NEW_PASSWORD})
    assert tampered.status_code == 400 and tampered.json()["detail"] == RESET_INVALID_DETAIL

    monkeypatch.setattr(AuthHelper, "RESET_TOKEN_MINUTES", -1)
    _forgot(client, "pat")
    expired = client.post("/auth/password/reset", json={"token": _token_from(outbox), "new_password": NEW_PASSWORD})
    assert expired.status_code == 400

    # A session token is not a reset token, however valid.
    session = client.post("/auth/login", json={"username": "pat", "password": PASSWORD}).json()["token"]
    assert client.post("/auth/password/reset", json={"token": session, "new_password": NEW_PASSWORD}).status_code == 400
    assert client.post("/auth/login", json={"username": "pat", "password": PASSWORD}).status_code == 200


def test_a_reset_token_is_never_accepted_as_a_session(client, make_farm, make_user, outbox):
    make_farm(FARM_A)
    make_user("pat")
    _forgot(client, "pat")
    token = _token_from(outbox)
    response = client.get("/zones/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_forgot_and_reset_are_rate_limited_per_ip(client, outbox):
    for _ in range(10):
        assert _forgot(client, "whoever").status_code == 202
    response = _forgot(client, "whoever")
    assert response.status_code == 429
    # Same window for reset: the cap is on the pair, not each separately.
    assert client.post("/auth/password/reset", json={"token": "x", "new_password": NEW_PASSWORD}).status_code == 429


def test_without_smtp_the_link_is_logged_instead_of_sent(client, make_farm, make_user, caplog):
    # No `outbox` fixture here: the real mailer runs, with SMTP_HOST unset.
    make_farm(FARM_A)
    make_user("pat")
    with caplog.at_level(logging.WARNING, logger="infrastructure.mail"):
        assert _forgot(client, "pat").status_code == 202
    logged = "\n".join(caplog.messages)
    assert "SMTP_HOST is not set" in logged and "pat@example.com" in logged and LINK.search(logged)


def test_a_reset_signs_every_live_session_out(client, make_farm, make_user, outbox, auth_headers):
    """The fingerprint in a session token stops matching once the password is reset (not only changed)."""
    make_farm(FARM_A)
    make_user("alice")
    live = auth_headers(username="alice")
    assert client.get("/auth/me", headers=live).status_code == 200
    _forgot(client, "alice")
    reset = client.post("/auth/password/reset", json={"token": _token_from(outbox), "new_password": "Another-Passw0rd"})
    assert reset.status_code == 204
    assert client.get("/auth/me", headers=live).status_code == 401
