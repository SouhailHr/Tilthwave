"""
PATCH contract: the web edit forms send the whole record back, identifiers included.
Identifiers are accepted and ignored; unknown fields are still rejected.
"""

from datetime import date

import pytest

from adapters.tree import TreeAdaptor
from tests.conftest import FARM_A


def test_zone_edit_form_payload_is_accepted_and_identifiers_ignored(client, auth_headers, make_farm, make_zone):
    make_farm()
    zone = make_zone("Zone A")
    edit_form = {
        "farm_name": "Other Farm",
        "zone_name": "Renamed",
        "size": 42,
        "soil_type": "Clay",
        "moisture_trigger_start": 40,
        "moisture_trigger_stop": 70,
        "saturation_trigger_start": 50,
        "saturation_trigger_stop": 85,
    }
    response = client.patch(f"/zones/{zone.id}", json=edit_form, headers=auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert (body["size"], body["soil_type"]) == (42, "Clay")
    assert (body["farm_name"], body["zone_name"]) == (FARM_A, "Zone A")


def test_farm_edit_form_payload(client, auth_headers, make_farm):
    farm = make_farm()
    response = client.patch(
        f"/farms/{farm.id}",
        json={"farm_name": "Renamed", "address": "2 Fig Road", "location": {}, "size": 9.5},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    assert (response.json()["farm_name"], response.json()["address"]) == (FARM_A, "2 Fig Road")


def test_tree_edit_form_payload(client, auth_headers, make_farm, make_zone, repos):
    make_farm()
    make_zone("Zone A")
    tree = repos.tree.create(
        TreeAdaptor.dict_to_entity(
            {
                "serial_number": "T1",
                "zone_name": "Zone A",
                "variety": "olive",
                "planting_date": date(2020, 1, 1),
                "height": 1.0,
                "width_diameter": 1.0,
                "trunk_diameter": 1.0,
            }
        )
    )
    response = client.patch(
        f"/trees/{tree.id}",
        json={"serial_number": "T-renamed", "variety": "fig", "height": 2.5},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    assert (response.json()["serial_number"], response.json()["variety"]) == ("T1", "fig")


@pytest.mark.parametrize(
    "resource,payload",
    [
        ("zones", {"colour": "green"}),
        ("users", {"is_admin": True}),
        ("trees", {"password": "x"}),
    ],
)
def test_unknown_fields_are_still_rejected(client, auth_headers, resource, payload):
    assert client.patch(f"/{resource}/1", json=payload, headers=auth_headers()).status_code == 422
