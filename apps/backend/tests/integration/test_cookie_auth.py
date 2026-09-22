"""
Browser sessions: httpOnly cookie auth, the CSRF check on cookie-authenticated mutations, and
the /auth/me and /auth/logout endpoints the web app relies on. Bearer auth (the simulator, curl,
Burp) must keep working exactly as before, with no cookies and no CSRF requirement.
"""

from tests.conftest import FARM_A, zone_payload

PASSWORD = "Passw0rd-Test!"  # make_user's default


def _set_cookie_headers(response) -> list[str]:
    return response.headers.get_list("set-cookie")


def _cookie_login(client, make_farm, make_user, username="cookie-admin", role="admin"):
    make_farm(FARM_A)
    make_user(username, role=role)
    response = client.post("/auth/login", json={"username": username, "password": PASSWORD, "use_cookie": True})
    assert response.status_code == 200
    return response


def test_cookie_login_sets_httponly_session_and_readable_csrf_cookies_and_no_body_token(client, make_farm, make_user):
    response = _cookie_login(client, make_farm, make_user)

    assert "token" not in response.json()
    assert response.json()["token_type"] == "cookie"
    cookies = _set_cookie_headers(response)
    access = next(c for c in cookies if c.startswith("tw_access="))
    csrf = next(c for c in cookies if c.startswith("tw_csrf="))
    assert "HttpOnly" in access and "SameSite=lax" in access and "Path=/" in access
    assert "HttpOnly" not in csrf  # the page must be able to read it to echo it back
    assert "Domain=" not in access  # host-only by default


def test_bearer_login_is_unchanged_no_cookies(client, make_farm, make_user):
    make_farm(FARM_A)
    make_user("api-client")
    response = client.post("/auth/login", json={"username": "api-client", "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer" and response.json()["token"]
    assert _set_cookie_headers(response) == []


def test_cookie_session_reads_protected_routes(client, make_farm, make_user):
    _cookie_login(client, make_farm, make_user)
    assert client.get("/zones/").status_code == 200
    assert client.get("/users/").status_code == 200


def test_cookie_mutation_needs_the_csrf_header(client, make_farm, make_user):
    _cookie_login(client, make_farm, make_user)

    response = client.post("/zones/", json=zone_payload())
    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF token missing or invalid"}

    response = client.post("/zones/", json=zone_payload(), headers={"X-CSRF-Token": "not-the-cookie"})
    assert response.status_code == 403

    response = client.post("/zones/", json=zone_payload(), headers={"X-CSRF-Token": client.cookies.get("tw_csrf")})
    assert response.status_code == 201


def test_bearer_mutation_needs_no_csrf_header(client, auth_headers, make_farm):
    make_farm()
    response = client.post("/zones/", json=zone_payload(), headers=auth_headers())
    assert response.status_code == 201


def test_me_reports_the_cookie_session_from_the_database(client, make_farm, make_user):
    _cookie_login(client, make_farm, make_user, username="carol", role="owner")
    response = client.get("/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "carol" and body["role"] == "owner" and body["farm_name"] == FARM_A
    assert isinstance(body["user_id"], int) and isinstance(body["exp"], int)


def test_me_is_401_without_a_session(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_logout_clears_the_session(client, make_farm, make_user):
    _cookie_login(client, make_farm, make_user)
    assert client.get("/auth/me").status_code == 200

    response = client.post("/auth/logout")
    assert response.status_code == 204
    cleared = _set_cookie_headers(response)
    assert any(c.startswith("tw_access=") for c in cleared) and any(c.startswith("tw_csrf=") for c in cleared)

    assert client.get("/auth/me").status_code == 401
    response = client.get("/zones/")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_deactivated_user_loses_the_cookie_session_immediately(client, make_farm, make_user, repos):
    _cookie_login(client, make_farm, make_user, username="mallory")
    assert client.get("/zones/").status_code == 200

    user = repos.users.first([{"attribute": "username", "value": "mallory", "condition": "eq"}])
    repos.users.update(user.id, {"is_active": False})

    response = client.get("/zones/")
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert client.get("/auth/me").status_code == 401


def test_tampered_cookie_is_401(client, make_farm, make_user):
    _cookie_login(client, make_farm, make_user)
    client.cookies.set("tw_access", client.cookies.get("tw_access") + "x")
    response = client.get("/zones/")
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
