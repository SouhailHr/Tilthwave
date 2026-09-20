from tests.conftest import zone_payload


def test_health_is_public_and_checks_the_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_missing_token_is_401_json(client):
    response = client.get("/users/")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_tampered_token_is_401_json(client, token_for):
    response = client.get("/users/", headers={"Authorization": f"Bearer {token_for()}x"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_read_only_role_cannot_patch(client, auth_headers, make_farm, make_zone):
    make_farm()
    zone = make_zone()
    response = client.patch(f"/zones/{zone.id}", json={"size": 5}, headers=auth_headers(role="worker"))
    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


def test_worker_may_update_trees(client, auth_headers):
    response = client.patch("/trees/999", json={"height": 2.0}, headers=auth_headers(role="worker"))
    assert response.status_code == 404  # authorized, then not found


def test_empty_list_is_a_page_not_a_404(client, auth_headers):
    response = client.get("/zones/", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_pagination_happens_in_the_database(client, auth_headers, make_farm, make_zone):
    make_farm()
    for i in range(7):
        make_zone(zone_name=f"Zone {i}")
    response = client.get("/zones/?page=2&size=3", headers=auth_headers())
    body = response.json()
    assert (body["total"], body["pages"], len(body["items"])) == (7, 3, 3)
    assert [z["zone_name"] for z in body["items"]] == ["Zone 3", "Zone 4", "Zone 5"]


def test_unknown_filter_attribute_is_400(client, auth_headers):
    response = client.get('/zones/?filters={"nope": 1}', headers=auth_headers())
    assert response.status_code == 400
    assert "nope" in response.json()["detail"]


def test_not_found_is_404_json(client, auth_headers):
    response = client.get("/zones/4242", headers=auth_headers())
    assert response.status_code == 404
    assert response.json() == {"detail": "Zone not found"}


def test_duplicate_is_409_without_sql_in_the_body(client, auth_headers, make_farm, make_zone):
    make_farm()
    make_zone(zone_name="Zone A")
    payload = zone_payload("Zone A")
    response = client.post("/zones/", json=payload, headers=auth_headers())
    assert response.status_code == 409
    assert "INSERT" not in response.json()["detail"]


def test_zone_triggers_must_be_consistent(client, auth_headers, make_farm):
    make_farm()
    payload = zone_payload("Zone X", moisture_trigger_start=80, moisture_trigger_stop=50)
    response = client.post("/zones/", json=payload, headers=auth_headers())
    assert response.status_code == 422


def test_create_returns_201_and_delete_returns_204(client, auth_headers, make_farm):
    make_farm()
    payload = zone_payload("Zone New")
    created = client.post("/zones/", json=payload, headers=auth_headers())
    assert created.status_code == 201
    deleted = client.delete(f"/zones/{created.json()['id']}", headers=auth_headers())
    assert deleted.status_code == 204
    assert client.get(f"/zones/{created.json()['id']}", headers=auth_headers()).status_code == 404


def test_login_is_rate_limited(client, make_farm, make_user):
    from interfaces.api.helpers.rate_limit import login_rate_limiter

    make_farm()
    make_user("jo", password="Passw0rd-Test!")
    responses = [
        client.post("/auth/login", json={"username": "jo", "password": "bad"})
        for _ in range(login_rate_limiter.limit + 1)
    ]
    assert [r.status_code for r in responses[:-1]] == [400] * login_rate_limiter.limit
    assert responses[-1].status_code == 429
    assert 0 < int(responses[-1].headers["retry-after"]) <= 60


def test_forwarded_for_from_an_untrusted_peer_does_not_reset_the_limit(client, make_farm, make_user):
    from interfaces.api.helpers.rate_limit import login_rate_limiter

    make_farm()
    make_user("jo", password="Passw0rd-Test!")
    statuses = [
        client.post(
            "/auth/login", json={"username": "jo", "password": "bad"}, headers={"X-Forwarded-For": f"203.0.113.{i}"}
        ).status_code
        for i in range(login_rate_limiter.limit + 1)
    ]
    assert statuses[-1] == 429


def test_forwarded_for_is_honoured_only_from_a_trusted_proxy(client, make_farm, make_user, monkeypatch):
    from config.settings import settings
    from interfaces.api.helpers.rate_limit import login_rate_limiter

    monkeypatch.setattr(settings.API, "TRUSTED_PROXIES", ["testclient"])
    make_farm()
    make_user("jo", password="Passw0rd-Test!")
    statuses = [
        client.post(
            "/auth/login", json={"username": "jo", "password": "bad"}, headers={"X-Forwarded-For": f"203.0.113.{i}"}
        ).status_code
        for i in range(login_rate_limiter.limit + 1)
    ]
    assert 429 not in statuses  # each hop is a different client behind the trusted proxy


def test_excluded_paths_match_exactly(client):
    assert client.get("/health").status_code == 200
    assert client.get("/healthz").status_code == 401  # not a prefix match


def test_docs_are_disabled_unless_enabled(client):
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404


def test_search_query_parameter_filters_by_identifier(client, auth_headers, make_farm, make_zone):
    make_farm()
    make_zone("Zone North")
    make_zone("Zone South")
    body = client.get("/zones/?search=north", headers=auth_headers()).json()
    assert [z["zone_name"] for z in body["items"]] == ["Zone North"]


def test_filter_on_a_non_column_attribute_is_400(client, auth_headers):
    assert client.get('/zones/?filters={"metadata": 1}', headers=auth_headers()).status_code == 400
    assert client.get('/users/?filters={"farm": "x"}', headers=auth_headers()).status_code == 400
