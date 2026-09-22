from common.tenant_context import get_current_tenant
from tests.conftest import FARM_A, FARM_B


def test_users_are_scoped_to_the_callers_farm(client, auth_headers, make_farm, make_user):
    make_farm(FARM_A)
    make_farm(FARM_B)
    make_user("alice", farm_name=FARM_A)
    make_user("bob", farm_name=FARM_B)
    page = client.get("/users/", headers=auth_headers(farm_name=FARM_A)).json()
    names = {u["username"] for u in page["items"]}
    assert "alice" in names and "bob" not in names  # "admin" is the caller's own row


def test_cross_farm_object_is_404_for_get_patch_and_delete(client, auth_headers, make_farm, make_zone):
    make_farm(FARM_A)
    make_farm(FARM_B)
    zone_b = make_zone("Zone B1", farm_name=FARM_B)
    headers = auth_headers(farm_name=FARM_A)
    assert client.get(f"/zones/{zone_b.id}", headers=headers).status_code == 404
    assert client.patch(f"/zones/{zone_b.id}", json={"size": 1}, headers=headers).status_code == 404
    assert client.delete(f"/zones/{zone_b.id}", headers=headers).status_code == 404


def test_create_cannot_assign_another_farm(client, auth_headers, make_farm, repos):
    make_farm(FARM_A)
    make_farm(FARM_B)
    payload = {
        "farm_name": FARM_B,
        "zone_name": "Zone Sneaky",
        "size": 10,
        "soil_type": "Loamy",
        "moisture_trigger_start": 50,
        "moisture_trigger_stop": 80,
        "saturation_trigger_start": 60,
        "saturation_trigger_stop": 90,
    }
    response = client.post("/zones/", json=payload, headers=auth_headers(farm_name=FARM_A))
    assert response.status_code == 201
    assert response.json()["farm_name"] == FARM_A  # bound to the caller's farm, not the body's
    assert repos.zone.get(response.json()["id"]).farm_name == FARM_A


def test_caller_without_farm_sees_nothing(client, auth_headers, make_farm, make_zone):
    make_farm(FARM_A)
    make_zone("Zone A")
    page = client.get("/zones/", headers=auth_headers(farm_name=None)).json()
    assert page["total"] == 0


def test_non_http_callers_run_unscoped(repos, make_farm, make_zone):
    make_farm(FARM_A)
    make_farm(FARM_B)
    make_zone("Zone A", farm_name=FARM_A)
    make_zone("Zone B", farm_name=FARM_B)
    assert get_current_tenant() is None
    assert len(repos.zone.filter([])) == 2
