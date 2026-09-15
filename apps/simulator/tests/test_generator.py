from config.settings import settings
from sensors.generator import PROFILES, generate_event, value_for


def test_values_climb_then_wrap_after_cycle_rounds():
    cycle = settings.SENSORS.CYCLE_ROUNDS
    assert value_for("moisture", 0) == PROFILES["moisture"][0]
    assert value_for("moisture", cycle - 1) == PROFILES["moisture"][0] + PROFILES["moisture"][1] * (cycle - 1)
    assert value_for("moisture", cycle) == value_for("moisture", 0)


def test_profiles_cross_the_demo_zone_triggers():
    """Start below the start triggers (50 / 60), end above the stop triggers (80 / 90)."""
    last = settings.SENSORS.CYCLE_ROUNDS - 1
    assert value_for("moisture", 0) < 50 and value_for("moisture", last) > 80
    assert value_for("saturation", 0) < 60 and value_for("saturation", last) > 90


def test_event_shape_matches_the_backend_contract():
    event = generate_event("moisture", "MSN1", 42)
    assert event["event_type"] == "data_record"
    assert event["sensor_serial_number"] == "MSN1"
    assert set(event["data"]) == {"value", "type", "timestamp"}
