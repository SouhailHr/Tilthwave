"""
Contract shapes: one 422 envelope with a fields map, HTTPExceptions in the same envelope,
`message` for success bodies with one login shape, ISO 8601 timestamps, and an item that reads
the same alone as in a page.
"""

from datetime import UTC, datetime

from adapters.sensor import SensorAdaptor
from adapters.zone_sensors import ZoneSensorsAdaptor
from common.dates import iso_utc, minutes_since, parse_db_datetime, utc_now
from tests.conftest import FARM_A, zone_payload


def test_schema_validation_uses_the_envelope_with_a_fields_map(client, auth_headers, make_farm):
    make_farm(FARM_A)
    body = {**zone_payload(), "size": "ten", "soil_type": None}
    response = client.post("/zones/", json=body, headers=auth_headers())
    assert response.status_code == 422
    envelope = response.json()
    assert envelope["error_code"] == "validation_error"
    assert envelope["request_id"] == response.headers["x-request-id"]
    assert set(envelope["fields"]) == {"size", "soil_type"}
    assert envelope["detail"].startswith("size: ")


def test_http_exceptions_use_the_envelope_and_keep_their_headers(client, make_farm, make_user):
    make_farm(FARM_A)
    make_user("alice")
    response = client.post("/auth/login", json={"username": "alice", "password": "wrong-password"})
    assert response.status_code == 400
    assert response.json()["error_code"] == "bad_request"
    assert response.json()["detail"] == "Incorrect username or password"
    unauthenticated = client.get("/zones/")
    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["www-authenticate"] == "Bearer"
    assert unauthenticated.json()["error_code"] == "unauthenticated"


def test_login_has_one_shape_on_both_channels(client, make_farm, make_user):
    make_farm(FARM_A)
    make_user("alice")
    bearer = client.post("/auth/login", json={"username": "alice", "password": "Passw0rd-Test!"}).json()
    cookie = client.post(
        "/auth/login", json={"username": "alice", "password": "Passw0rd-Test!", "use_cookie": True}
    ).json()
    assert set(bearer) == set(cookie) == {"token", "token_type", "expires_in"}
    assert bearer["token"] and bearer["token_type"] == "bearer"
    assert cookie["token"] is None and cookie["token_type"] == "cookie"
    assert bearer["expires_in"] == cookie["expires_in"] > 0


def test_timestamps_are_iso_8601_with_a_utc_offset_and_parse_back_to_naive_utc(repos, make_farm):
    make_farm(FARM_A)
    sensor = repos.sensor.create(
        SensorAdaptor.dict_to_entity({"serial_number": "S1", "type": "moisture_sensor", "is_active": True})
    )
    assert sensor.created_date.endswith("+00:00") and "T" in sensor.created_date
    parsed = parse_db_datetime(sensor.created_date)
    assert parsed.tzinfo is None and abs((utc_now() - parsed).total_seconds()) < 5
    assert 0 <= minutes_since(sensor.created_date) < 1
    # the older naive form is still understood, and an explicit non-UTC offset is converted
    assert parse_db_datetime("2026-09-15 16:06:56") == datetime(2026, 9, 15, 16, 6, 56)
    assert parse_db_datetime("2026-09-15T18:06:56+02:00") == datetime(2026, 9, 15, 16, 6, 56)
    assert iso_utc(datetime(2026, 9, 15, 16, 6, 56)) == "2026-09-15T16:06:56+00:00"
    assert iso_utc(datetime(2026, 9, 15, 18, 6, 56, tzinfo=UTC)) == "2026-09-15T18:06:56+00:00"


def test_a_sensor_reads_the_same_alone_as_in_the_list(client, auth_headers, make_farm, make_zone, repos):
    make_farm(FARM_A)
    make_zone("Zone A")
    sensor = repos.sensor.create(
        SensorAdaptor.dict_to_entity(
            {"serial_number": "M1", "type": "moisture_sensor", "is_active": True, "farm_name": FARM_A}
        )
    )
    repos.zone_sensors.create(ZoneSensorsAdaptor.dict_to_entity({"zone_name": "Zone A", "sensor_serial_number": "M1"}))
    headers = auth_headers()
    listed = client.get("/sensors/", headers=headers).json()["items"][0]
    alone = client.get(f"/sensors/{sensor.id}", headers=headers).json()
    assert alone == listed
    assert alone["assigned_to"] == "Zone A"
