"""
Who may change whom (core/use_cases/users.py), what a hijacked session cannot do to the account
it holds, the farm every account must belong to, the audit trail and the response headers.
"""

import logging

import pytest

from common.tenant_context import reset_tenant, set_tenant
from tests.conftest import FARM_A

PASSWORD = "Passw0rd-Test!"  # make_user's default


def _payload(username, role):
    return {
        "username": username,
        "email": f"{username}@example.com",
        "phone_number": "+000",
        "text_password": "Str0ng-Passw0rd",
        "first_name": "New",
        "last_name": "Bie",
        "role": role,
        "farm_name": FARM_A,
    }


def _id(repos, username):
    return repos.users.first([{"attribute": "username", "value": username, "condition": "eq"}]).id


# ---- owner is the only role that manages admins and owners ------------------------------------


@pytest.mark.parametrize("role", ["admin", "owner"])
def test_only_an_owner_creates_an_admin_or_owner(client, auth_headers, make_farm, role):
    make_farm()
    admin = auth_headers(username="adm", role="admin")
    refused = client.post("/users/", json=_payload("new", role), headers=admin)
    assert refused.status_code == 403 and refused.json()["error_code"] == "forbidden"
    assert (
        client.post(
            "/users/", json=_payload("new", role), headers=auth_headers(username="own", role="owner")
        ).status_code
        == 201
    )
    # an admin still manages the observing roles
    assert client.post("/users/", json=_payload("w", "worker"), headers=admin).status_code == 201


def test_an_admin_cannot_appoint_change_deactivate_or_delete_an_admin_or_owner(
    client, auth_headers, make_farm, make_user, repos
):
    make_farm()
    admin = auth_headers(username="adm", role="admin")
    make_user("own", role="owner")
    make_user("other-admin", role="admin")
    worker = make_user("w", role="worker")
    for target in ("own", "other-admin"):
        uid = _id(repos, target)
        assert client.patch(f"/users/{uid}", json={"first_name": "X"}, headers=admin).status_code == 403
        assert client.patch(f"/users/{uid}", json={"is_active": False}, headers=admin).status_code == 403
        assert (
            client.patch(f"/users/{uid}", json={"text_password": "Another-Passw0rd"}, headers=admin).status_code == 403
        )
        assert client.delete(f"/users/{uid}", headers=admin).status_code == 403
    for role in ("admin", "owner"):
        assert client.patch(f"/users/{worker.id}", json={"role": role}, headers=admin).status_code == 403
    assert client.patch(f"/users/{worker.id}", json={"role": "engineer"}, headers=admin).status_code == 200
    assert client.delete(f"/users/{worker.id}", headers=admin).status_code == 204


def test_an_owner_manages_everyone(client, auth_headers, make_farm, make_user, repos):
    make_farm()
    owner = auth_headers(username="own", role="owner")
    make_user("own2", role="owner")
    adm = make_user("adm", role="admin")
    assert client.patch(f"/users/{adm.id}", json={"role": "worker"}, headers=owner).status_code == 200
    assert client.patch(f"/users/{_id(repos, 'own2')}", json={"role": "admin"}, headers=owner).status_code == 200
    assert client.delete(f"/users/{_id(repos, 'own2')}", headers=owner).status_code == 204


# ---- nobody through /users on themselves ---------------------------------------------------------


def test_own_role_status_and_password_are_not_changed_through_users(client, auth_headers, make_farm, repos):
    make_farm()
    owner = auth_headers(username="own", role="owner")
    me = _id(repos, "own")
    for body in ({"role": "worker"}, {"is_active": False}, {"text_password": "Another-Passw0rd"}):
        response = client.patch(f"/users/{me}", json=body, headers=owner)
        assert response.status_code == 422, body
        assert response.json()["error_code"] == "unprocessable"
    assert client.patch(f"/users/{me}", json={"first_name": "Still"}, headers=owner).status_code == 200
    assert client.delete(f"/users/{me}", headers=owner).status_code == 422
    assert client.get("/auth/me", headers=owner).status_code == 200  # still signed in, still an owner


# ---- the last owner stays ------------------------------------------------------------------------


def test_the_last_active_owner_cannot_be_demoted_deactivated_or_deleted(make_farm, make_user, repos, use_cases):
    """
    Through HTTP the rule is unreachable in a legal way: an owner acting on the last owner is
    acting on themselves (refused earlier), and an admin may not touch an owner at all. It guards
    the use case itself, for scripts and any future caller, so it is exercised there.
    """
    make_farm()
    solo = make_user("solo", role="owner")
    actor = make_user("boss", role="owner")
    token = set_tenant(
        {"user_id": actor.id, "username": "boss", "farm_name": FARM_A, "role": "owner", "is_superuser": True}
    )
    try:
        repos.users.update(actor.id, {"role": "admin"})  # boss steps down: solo is now the last owner
        for body in ({"role": "admin"}, {"is_active": False}):
            with pytest.raises(Exception, match="last active owner"):
                use_cases.users.update(solo.id, dict(body))
        with pytest.raises(Exception, match="last active owner"):
            use_cases.users.delete(solo.id)
        assert repos.users.get(solo.id).role == "owner" and repos.users.get(solo.id).is_active
    finally:
        reset_tenant(token)


# ---- the account a hijacked session holds ---------------------------------------------------------


def test_changing_the_email_needs_the_current_password(client, auth_headers, make_farm, repos):
    make_farm()
    headers = auth_headers(username="pat", role="worker")
    without = client.patch("/account/profile", json={"email": "attacker@example.com"}, headers=headers)
    assert without.status_code == 422 and "password" in without.json()["detail"].lower()
    wrong = client.patch(
        "/account/profile", json={"email": "attacker@example.com", "current_password": "nope"}, headers=headers
    )
    assert wrong.status_code == 422
    assert repos.users.get(_id(repos, "pat")).email == "pat@example.com"
    ok = client.patch(
        "/account/profile", json={"email": "pat2@example.com", "current_password": PASSWORD}, headers=headers
    )
    assert ok.status_code == 200 and ok.json()["email"] == "pat2@example.com"
    # the same email again, or other fields, need no password
    assert (
        client.patch(
            "/account/profile", json={"email": "pat2@example.com", "first_name": "P"}, headers=headers
        ).status_code
        == 200
    )


def test_is_superuser_is_not_accepted_on_create(client, auth_headers, make_farm):
    make_farm()
    body = {**_payload("new", "worker"), "is_superuser": True}
    response = client.post("/users/", json=body, headers=auth_headers(username="own", role="owner"))
    assert response.status_code == 422 and "is_superuser" in response.json()["fields"]


def test_login_body_has_length_limits(client):
    assert client.post("/auth/login", json={"username": "a" * 51, "password": "x"}).status_code == 422
    assert client.post("/auth/login", json={"username": "a", "password": "x" * 73}).status_code == 422


# ---- the audit trail -----------------------------------------------------------------------------


def test_auth_events_are_audited(client, auth_headers, make_farm, make_user, repos, caplog):
    make_farm()
    make_user("alice", role="worker")
    owner = auth_headers(username="own", role="owner")
    with caplog.at_level(logging.INFO, logger="audit"):
        client.post("/auth/login", json={"username": "alice", "password": "wrong"})
        token = client.post("/auth/login", json={"username": "alice", "password": PASSWORD}).json()["token"]
        client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        uid = _id(repos, "alice")
        client.patch(f"/users/{uid}", json={"role": "engineer"}, headers=owner)
        client.patch(f"/users/{uid}", json={"is_active": False}, headers=owner)
        client.delete(f"/users/{uid}", headers=owner)
    events = [r.getMessage() for r in caplog.records if r.name == "audit"]
    assert any(e.startswith("event=login.failure username=alice") and "reason=credentials" in e for e in events)
    assert any(e.startswith("event=login.success username=alice role=worker channel=header") for e in events)
    assert any(e.startswith("event=logout username=alice") for e in events)
    assert any(e == "event=user.role_change actor=own user=alice old=worker new=engineer" for e in events)
    assert any(e == "event=user.deactivate actor=own user=alice" for e in events)
    assert any(e == "event=user.delete actor=own user=alice role=engineer" for e in events)
    assert all(r.request_id != "-" for r in caplog.records if r.name == "audit")


# ---- headers -----------------------------------------------------------------------------------


def test_every_response_carries_the_security_headers(client, auth_headers, make_farm):
    make_farm()
    for response in (client.get("/health"), client.get("/zones/", headers=auth_headers()), client.get("/nope")):
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cache-control"] == "no-store"
