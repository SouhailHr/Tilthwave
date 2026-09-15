import pytest


def test_seed_is_idempotent_including_initial_records(repos):
    from infrastructure.scripts import seed_data

    seed_data.main()
    seed_data.main()
    assert len(repos.users.filter([])) == 1
    assert len(repos.zone.filter([])) == 2
    assert len(repos.sensor_record.filter([])) == 6  # not 12: readings are written once per sensor
    admin = repos.users.first([{"attribute": "username", "value": "admin", "condition": "eq"}])
    assert admin.is_superuser and admin.farm_name == "Sunny Farms" and admin.password.startswith("$2b$")


def test_seed_refuses_to_run_without_admin_password(monkeypatch):
    from infrastructure.scripts import seed_data

    monkeypatch.delenv("ADMIN_PASSWORD")
    seed_data.seed_farm()
    with pytest.raises(SystemExit, match="ADMIN_PASSWORD"):
        seed_data.seed_admin()
