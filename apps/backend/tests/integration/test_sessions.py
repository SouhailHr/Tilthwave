"""
Server-side sessions (core/use_cases/user_session.py): a token is only as alive as the row it
names. Logout ends it at once, idle and absolute limits end it on their own, "sign out
everywhere" ends the others, and the per-account lockout bounds guessing from any number of
addresses. The signature alone never authenticates.
"""

from datetime import timedelta

import jwt
import pytest

from common.dates import utc_now
from config.settings import settings
from core.use_cases import user_session as sessions_module
from infrastructure.database.tables.user_session import UserSession
from interfaces.api.helpers.auth import JWT_ISSUER, AuthHelper
from tests.conftest import FARM_A

PASSWORD = "Passw0rd-Test!"  # make_user's default


def _login(client, username, use_cookie=False, **extra):
    body = {"username": username, "password": PASSWORD, "use_cookie": use_cookie, **extra}
    response = client.post("/auth/login", json=body)
    assert response.status_code == 200, response.text
    return response


def _bearer(client, username):
    return {"Authorization": f"Bearer {_login(client, username).json()['token']}"}


def _set(repos, token_id, **columns):
    with repos.user_session.Session() as session:
        row = session.query(UserSession).filter(UserSession.token_id == token_id).one()
        for name, value in columns.items():
            setattr(row, name, value)
        session.commit()


def _sign(claims, algorithm="HS256"):
    return jwt.encode(claims, settings.API.SECRET_KEY, algorithm=algorithm)


def _only_session(repos):
    rows = repos.user_session.filter([])
    assert len(rows) == 1
    return rows[0]


# ---- the token names a live row --------------------------------------------------------------


def test_login_opens_a_session_the_token_names(client, make_farm, make_user, repos):
    make_farm(FARM_A)
    alice = make_user("alice")
    token = _login(client, "alice").json()["token"]
    claims = jwt.decode(token, options={"verify_signature": False})
    row = _only_session(repos)
    assert claims["jti"] == row.token_id and claims["iss"] == JWT_ISSUER and "iat" in claims
    assert row.user_id == alice.id and row.channel == "header" and row.revoked_at is None
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_logout_ends_the_bearer_session_at_once(client, make_farm, make_user):
    """The finding this PR exists for: a token copied off a device died only with its exp."""
    make_farm(FARM_A)
    make_user("alice")
    headers = _bearer(client, "alice")
    assert client.get("/zones/", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 204
    response = client.get("/zones/", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"
    # Signing out an already-ended session is harmless.
    assert client.post("/auth/logout", headers=headers).status_code == 204


def test_logout_ends_the_cookie_session_not_only_the_cookies(client, make_farm, make_user, repos):
    make_farm(FARM_A)
    make_user("alice")
    _login(client, "alice", use_cookie=True)
    stolen = client.cookies.get("tw_access")
    assert client.post("/auth/logout", headers={"X-CSRF-Token": client.cookies.get("tw_csrf")}).status_code == 204
    client.cookies.clear()
    client.cookies.set("tw_access", stolen)
    assert client.get("/auth/me").status_code == 401
    assert _only_session(repos).revoked_at is not None


def test_idle_sessions_end_and_active_ones_are_touched(client, make_farm, make_user, repos, monkeypatch):
    make_farm(FARM_A)
    make_user("alice")
    headers = _bearer(client, "alice")
    token_id = _only_session(repos).token_id
    idle = settings.API.SESSION_IDLE_MINUTES

    _set(repos, token_id, last_seen=utc_now() - timedelta(minutes=idle - 1))
    assert client.get("/zones/", headers=headers).status_code == 200
    assert utc_now() - sessions_module.parse_db_datetime(_only_session(repos).last_seen) < timedelta(seconds=5)

    _set(repos, token_id, last_seen=utc_now() - timedelta(minutes=idle + 1))
    assert client.get("/zones/", headers=headers).status_code == 401
    # Once idle, activity cannot revive it: the row stays where it was.
    assert utc_now() - sessions_module.parse_db_datetime(_only_session(repos).last_seen) > timedelta(minutes=idle)


def test_a_session_ends_at_its_absolute_limit_even_when_busy(client, make_farm, make_user, repos):
    make_farm(FARM_A)
    make_user("alice")
    headers = _bearer(client, "alice")
    token_id = _only_session(repos).token_id
    _set(repos, token_id, expires_at=utc_now() - timedelta(seconds=1), last_seen=utc_now())
    assert client.get("/zones/", headers=headers).status_code == 401


def test_last_seen_is_written_at_most_once_per_interval(client, make_farm, make_user, repos, count_statements):
    make_farm(FARM_A)
    make_user("alice")
    headers = _bearer(client, "alice")
    _set(
        repos,
        _only_session(repos).token_id,
        last_seen=utc_now() - timedelta(seconds=sessions_module.TOUCH_INTERVAL_SECONDS + 1),
    )
    with count_statements as counted:
        client.get("/health", headers=headers)  # public, but the middleware still resolves the session
    touched = counted.n
    with count_statements as counted:
        client.get("/health", headers=headers)
    assert counted.n == touched - 1  # the UPDATE of last_seen ran once, on the first request


def test_a_session_of_another_user_does_not_authenticate_a_token(client, make_farm, make_user, repos):
    make_farm(FARM_A)
    alice = make_user("alice")
    make_user("bob")
    _login(client, "bob")
    bobs = _only_session(repos)
    forged = AuthHelper.encode(
        {"user_id": alice.id, "username": "alice", "role": "admin", "farm_name": FARM_A, "jti": bobs.token_id},
        utc_now() + timedelta(hours=1),
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


@pytest.mark.parametrize(
    "tamper",
    [
        pytest.param(lambda c: _sign(c, "HS384"), id="other-algorithm"),
        pytest.param(
            lambda c: jwt.encode({**c, "iss": "someone-else"}, settings.API.SECRET_KEY, algorithm="HS256"), id="issuer"
        ),
        pytest.param(
            lambda c: jwt.encode(
                {k: v for k, v in c.items() if k != "iat"}, settings.API.SECRET_KEY, algorithm="HS256"
            ),
            id="no-iat",
        ),
    ],
)
def test_the_algorithm_and_issuer_are_pinned(client, make_farm, make_user, tamper):
    make_farm(FARM_A)
    make_user("alice")
    token = _login(client, "alice").json()["token"]
    claims = jwt.decode(token, options={"verify_signature": False})
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {tamper(claims)}"}).status_code == 401


# ---- ending sessions from elsewhere ----------------------------------------------------------


def test_deactivation_and_an_admin_set_password_end_the_sessions(client, make_farm, make_user, repos, auth_headers):
    make_farm(FARM_A)
    make_user("alice", role="worker")
    admin = auth_headers(username="boss")
    alice_id = repos.users.first([{"attribute": "username", "value": "alice", "condition": "eq"}]).id
    headers = _bearer(client, "alice")

    assert (
        client.patch(f"/users/{alice_id}", json={"text_password": "Another-Passw0rd"}, headers=admin).status_code == 200
    )
    assert client.get("/auth/me", headers=headers).status_code == 401
    assert repos.user_session.first([{"attribute": "user_id", "value": alice_id, "condition": "eq"}]).revoked_at

    client.post("/auth/login", json={"username": "alice", "password": "Another-Passw0rd"})
    live = repos.user_session.filter([{"attribute": "revoked_at", "value": None, "condition": "eq"}])
    assert [s.user_id for s in live if s.user_id == alice_id]
    assert client.patch(f"/users/{alice_id}", json={"is_active": False}, headers=admin).status_code == 200
    assert not [
        s
        for s in repos.user_session.filter([{"attribute": "revoked_at", "value": None, "condition": "eq"}])
        if s.user_id == alice_id
    ]


def test_deleting_a_user_ends_their_sessions(client, make_farm, make_user, repos, auth_headers):
    make_farm(FARM_A)
    make_user("alice", role="worker")
    admin = auth_headers(username="boss")
    alice_id = repos.users.first([{"attribute": "username", "value": "alice", "condition": "eq"}]).id
    headers = _bearer(client, "alice")
    assert client.delete(f"/users/{alice_id}", headers=admin).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_ended_sessions_are_purged_at_the_next_login(client, make_farm, make_user, repos):
    make_farm(FARM_A)
    make_user("alice")
    _bearer(client, "alice")
    old = _only_session(repos)
    _set(repos, old.token_id, revoked_at=utc_now() - timedelta(days=sessions_module.PURGE_AFTER_DAYS + 1))
    _login(client, "alice")
    assert [s.token_id for s in repos.user_session.filter([])] != [old.token_id]
    assert len(repos.user_session.filter([])) == 1


# ---- the sessions list -----------------------------------------------------------------------


def test_sessions_list_shows_the_live_ones_and_flags_the_current(client, make_farm, make_user, repos):
    make_farm(FARM_A)
    make_user("alice")
    phone = _bearer(client, "alice")
    laptop = _login(client, "alice", use_cookie=True)
    assert laptop.json()["token"] is None

    response = client.get("/account/sessions")  # cookie session = the laptop
    assert response.status_code == 200
    items = response.json()["items"]
    assert [s["current"] for s in items] == [True, False]  # newest first
    assert {s["channel"] for s in items} == {"cookie", "header"}
    assert all("token_id" not in s and set(s) >= {"id", "last_seen", "expires_at", "created_date"} for s in items)

    csrf = {"X-CSRF-Token": client.cookies.get("tw_csrf")}
    phone_id = next(s["id"] for s in items if not s["current"])
    assert client.delete(f"/account/sessions/{phone_id}", headers=csrf).status_code == 204
    assert client.get("/zones/", headers=phone).status_code == 401
    assert client.delete(f"/account/sessions/{phone_id}", headers=csrf).status_code == 404  # already ended
    assert [s["current"] for s in client.get("/account/sessions").json()["items"]] == [True]


def test_sign_out_everywhere_else_keeps_this_session(client, make_farm, make_user):
    make_farm(FARM_A)
    make_user("alice")
    devices = [_bearer(client, "alice") for _ in range(3)]
    here = _bearer(client, "alice")
    response = client.delete("/account/sessions", headers=here)
    assert response.status_code == 200 and response.json()["revoked"] == 3
    assert all(client.get("/auth/me", headers=d).status_code == 401 for d in devices)
    assert client.get("/auth/me", headers=here).status_code == 200


def test_another_users_session_is_not_found(client, make_farm, make_user, repos):
    make_farm(FARM_A)
    make_user("alice"), make_user("bob")
    _bearer(client, "bob")
    bobs = _only_session(repos)
    alice = _bearer(client, "alice")
    assert client.delete(f"/account/sessions/{bobs.id}", headers=alice).status_code == 404
    assert client.get("/auth/me", headers=alice).status_code == 200
    assert repos.user_session.get(bobs.id).revoked_at is None


def test_every_role_can_manage_its_own_sessions(client, make_farm, make_user):
    make_farm(FARM_A)
    make_user("worker", role="worker")
    headers = _bearer(client, "worker")
    assert client.get("/account/sessions", headers=headers).status_code == 200
    assert client.delete("/account/sessions", headers=headers).status_code == 200


# ---- per-account lockout ---------------------------------------------------------------------


def test_the_account_locks_after_too_many_failures_whatever_the_address(client, make_farm, make_user):
    make_farm(FARM_A)
    make_user("alice")
    make_user("bob")
    for _ in range(settings.API.LOGIN_FAILURES_PER_ACCOUNT):
        assert client.post("/auth/login", json={"username": "alice", "password": "wrong"}).status_code == 400
    locked = client.post("/auth/login", json={"username": "Alice ", "password": PASSWORD})  # right password
    assert locked.status_code == 429 and locked.headers["retry-after"]
    assert locked.json()["error_code"] == "rate_limited"
    # Another account is unaffected, and the per-IP window (10/min) has not been reached.
    assert client.post("/auth/login", json={"username": "bob", "password": PASSWORD}).status_code == 200


def test_a_successful_login_clears_the_failure_count(client, make_farm, make_user):
    make_farm(FARM_A)
    make_user("alice")
    for _ in range(settings.API.LOGIN_FAILURES_PER_ACCOUNT - 1):
        client.post("/auth/login", json={"username": "alice", "password": "wrong"})
    assert client.post("/auth/login", json={"username": "alice", "password": PASSWORD}).status_code == 200
    for _ in range(settings.API.LOGIN_FAILURES_PER_ACCOUNT - 1):
        client.post("/auth/login", json={"username": "alice", "password": "wrong"})
    assert client.post("/auth/login", json={"username": "alice", "password": PASSWORD}).status_code == 200
