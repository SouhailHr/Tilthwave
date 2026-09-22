"""
URL shape is part of the contract: collections end with a slash, items do not, and a mismatch is
a 404 rather than a redirect (see the FastAPI construction in interfaces/api/main.py).
"""

from tests.conftest import FARM_A


def test_item_routes_have_no_trailing_slash_and_are_not_redirected(client, auth_headers, make_farm, make_zone):
    make_farm(FARM_A)
    zone = make_zone("Zone A")
    headers = auth_headers()
    assert client.get(f"/zones/{zone.id}", headers=headers).status_code == 200
    response = client.get(f"/zones/{zone.id}/", headers=headers, follow_redirects=False)
    assert response.status_code == 404


def test_collection_routes_end_with_a_slash_and_are_not_redirected(client, auth_headers, make_farm):
    make_farm(FARM_A)
    headers = auth_headers()
    assert client.get("/zones/", headers=headers).status_code == 200
    assert client.get("/zones", headers=headers, follow_redirects=False).status_code == 404


def test_login_has_no_trailing_slash(client, make_farm, make_user):
    make_farm(FARM_A)
    make_user("alice")
    body = {"username": "alice", "password": "Passw0rd-Test!"}
    assert client.post("/auth/login", json=body).status_code == 200
    assert client.post("/auth/login/", json=body, follow_redirects=False).status_code == 404
