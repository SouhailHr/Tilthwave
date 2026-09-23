"""
/account: the caller's own profile and password, self-service for every role, own row only.
"""

from tests.conftest import FARM_A

PASSWORD = "Passw0rd-Test!"  # make_user's default
NEW_PASSWORD = "N3w-Passw0rd-Test!"


def _cookie_login(client, username, password=PASSWORD):
    response = client.post("/auth/login", json={"username": username, "password": password, "use_cookie": True})
    assert response.status_code == 200
    return {"X-CSRF-Token": client.cookies.get("tw_csrf")}


def _bearer_login(client, username, password=PASSWORD):
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_profile_is_the_callers_own_row_for_every_role(client, auth_headers, make_farm):
    make_farm(FARM_A)
    for role in ("admin", "owner", "worker", "engineer"):
        response = client.get("/account/profile", headers=auth_headers(username=f"u-{role}", role=role))
        assert response.status_code == 200, role
        body = response.json()
        assert body["username"] == f"u-{role}" and body["role"] == role
        assert "password" not in body


def test_a_farm_less_account_can_still_see_itself(client, auth_headers, make_user):
    # An authenticated caller with no farm sees no tenant rows; their own row must be the exception.
    make_user("bootstrap", farm_name=None)
    response = client.get("/account/profile", headers=auth_headers(username="bootstrap", farm_name=None))
    assert response.status_code == 200
    assert response.json()["username"] == "bootstrap" and response.json()["farm_name"] is None


def test_profile_patch_updates_contact_details_only(client, auth_headers, make_farm, repos):
    make_farm(FARM_A)
    headers = auth_headers(username="wendy", role="worker")

    response = client.patch("/account/profile", json={"first_name": "Wendy", "phone_number": "+123"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Wendy" and response.json()["phone_number"] == "+123"
    assert response.json()["performed_by"] == "wendy"

    for forbidden in ({"role": "admin"}, {"is_active": False}, {"farm_name": "Elsewhere"}, {"text_password": "x" * 8}):
        assert client.patch("/account/profile", json=forbidden, headers=headers).status_code == 422, forbidden
    row = repos.users.first([{"attribute": "username", "value": "wendy", "condition": "eq"}])
    assert row.role == "worker" and row.is_active and row.farm_name == FARM_A


def test_change_password_rejects_a_wrong_current_password_and_changes_nothing(client, make_farm, make_user):
    make_farm(FARM_A)
    make_user("pat")
    headers = _bearer_login(client, "pat")

    response = client.post(
        "/account/password", json={"current_password": "not-it", "new_password": NEW_PASSWORD}, headers=headers
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Current password is incorrect"
    assert client.post("/auth/login", json={"username": "pat", "password": PASSWORD}).status_code == 200


def test_change_password_enforces_the_minimum_length(client, make_farm, make_user):
    make_farm(FARM_A)
    make_user("pat")
    headers = _bearer_login(client, "pat")
    response = client.post(
        "/account/password", json={"current_password": PASSWORD, "new_password": "short"}, headers=headers
    )
    assert response.status_code == 422


def test_change_password_rotates_this_cookie_session_and_signs_the_others_out(client, make_farm, make_user):
    make_farm(FARM_A)
    make_user("pat")
    other_device = _bearer_login(client, "pat")  # before the cookie login: an empty jar, no CSRF needed
    csrf = _cookie_login(client, "pat")
    assert client.get("/zones/", headers=other_device).status_code == 200

    response = client.post(
        "/account/password", json={"current_password": PASSWORD, "new_password": NEW_PASSWORD}, headers=csrf
    )
    assert response.status_code == 200
    assert response.json()["token"] is None  # re-issued as cookies, never in a body JS can read
    assert any(c.startswith("tw_access=") for c in response.headers.get_list("set-cookie"))

    # This browser: still signed in, on the re-issued cookie.
    assert client.get("/auth/me").status_code == 200
    assert client.get("/zones/").status_code == 200
    # The other device: its session was ended by the change.
    response = client.get("/zones/", headers=other_device)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"
    # And only the new password logs in now. The jar still holds the re-issued session cookie, so
    # these POSTs are cookie-authenticated and must carry the (rotated) CSRF header, exactly as
    # the browser does; without it the CSRF gate answers 403 before login is even looked at.
    csrf = {"X-CSRF-Token": client.cookies.get("tw_csrf")}
    stale = client.post("/auth/login", json={"username": "pat", "password": PASSWORD}, headers=csrf)
    assert stale.status_code == 400
    fresh = client.post("/auth/login", json={"username": "pat", "password": NEW_PASSWORD}, headers=csrf)
    assert fresh.status_code == 200


def test_change_password_returns_a_fresh_token_to_a_bearer_client(client, make_farm, make_user):
    make_farm(FARM_A)
    make_user("pat")
    old = _bearer_login(client, "pat")

    response = client.post(
        "/account/password", json={"current_password": PASSWORD, "new_password": NEW_PASSWORD}, headers=old
    )
    assert response.status_code == 200
    new = {"Authorization": f"Bearer {response.json()['token']}"}
    assert client.get("/zones/", headers=new).status_code == 200
    assert client.get("/zones/", headers=old).status_code == 401


def test_account_needs_a_session(client):
    assert client.get("/account/profile").status_code == 401
    assert client.post("/account/password", json={"current_password": "x", "new_password": "x" * 8}).status_code == 401
