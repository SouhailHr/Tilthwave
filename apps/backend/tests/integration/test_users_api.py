from tests.conftest import FARM_A


def _user_payload(username="newbie", **overrides):
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "phone_number": "+000",
        "text_password": "Str0ng-Passw0rd",
        "first_name": "New",
        "last_name": "Bie",
        "role": "worker",
        "farm_name": FARM_A,
    }
    payload.update(overrides)
    return payload


def test_create_user_returns_201_without_password_and_persists_the_hash(client, auth_headers, make_farm, repos):
    make_farm()
    response = client.post("/users/", json=_user_payload(), headers=auth_headers())
    assert response.status_code == 201
    body = response.json()
    assert "password" not in body and "text_password" not in body
    assert body["performed_by"] == "admin"  # from the caller's token, not a literal
    stored = repos.users.get(body["id"])
    assert stored.password.startswith("$2b$")


def test_created_user_can_log_in(client, auth_headers, make_farm):
    make_farm()
    client.post("/users/", json=_user_payload(), headers=auth_headers())
    response = client.post("/auth/login", json={"username": "newbie", "password": "Str0ng-Passw0rd"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_list_and_get_never_expose_the_hash(client, auth_headers, make_farm, make_user):
    make_farm()
    user = make_user("jo")
    page = client.get("/users/", headers=auth_headers()).json()
    assert page["total"] == 2 and all("password" not in item for item in page["items"])  # jo + the caller
    assert "password" not in client.get(f"/users/{user.id}", headers=auth_headers()).json()


def test_patch_role_derives_superuser_and_rejects_unknown_fields(client, auth_headers, make_farm, make_user):
    make_farm()
    user = make_user("jo", role="worker")
    owner = auth_headers(username="boss", role="owner")  # appointing an owner is an owner's act
    ok = client.patch(f"/users/{user.id}", json={"role": "owner"}, headers=owner)
    assert ok.status_code == 200 and ok.json()["is_superuser"] is True
    # identifiers echoed by edit forms are accepted and ignored: the farm never changes through PATCH
    moved = client.patch(f"/users/{user.id}", json={"farm_name": "Other Farm"}, headers=owner)
    assert moved.status_code == 200 and moved.json()["farm_name"] == FARM_A
    hashed = client.patch(f"/users/{user.id}", json={"password": "$2b$fake"}, headers=owner)
    assert hashed.status_code == 422


def test_patch_text_password_changes_the_login_password(client, auth_headers, make_farm, make_user):
    make_farm()
    user = make_user("jo", role="worker", password="Old-Passw0rd!")
    response = client.patch(f"/users/{user.id}", json={"text_password": "New-Passw0rd!"}, headers=auth_headers())
    assert response.status_code == 200 and "password" not in response.json()
    assert client.post("/auth/login", json={"username": "jo", "password": "Old-Passw0rd!"}).status_code == 400
    assert client.post("/auth/login", json={"username": "jo", "password": "New-Passw0rd!"}).status_code == 200


def test_login_with_wrong_password_is_400(client, make_farm, make_user):
    make_farm()
    make_user("jo")
    response = client.post("/auth/login", json={"username": "jo", "password": "nope"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect username or password"
