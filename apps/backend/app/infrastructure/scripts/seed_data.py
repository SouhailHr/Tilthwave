"""
Seed a deterministic demo dataset.

Idempotent: re-running skips entities that already exist (matched by their
unique business key). Designed so that on the next flow-runner tick:
  - Zone A trips the irrigation START trigger (low moisture + low saturation)
  - Zone B sits idle (readings above start trigger, below stop trigger)

Sensor serials match the Sensor Mocker's ZONES dict so the mocker can target
this DB unchanged.

Linkage:
  Sunny Farms
    └─ admin user (farm_name=Sunny Farms)
    └─ Zone A
        ├─ trees: TREEA001..TREEA003 (olive)
        ├─ sensors: TSN123456 (temp), MSN123456 (moisture), SAT123456 (saturation)
        └─ water switcher SWITA01 (sensor SWA001) → water source WS001
    └─ Zone B
        ├─ trees: TREEB001..TREEB002 (fig)
        ├─ sensors: TSN123457, MSN123457, SAT123457
        └─ water switcher SWITB01 (sensor SWB001) → water source WS001
    └─ water source WS001 (sensor SRC001)

Usage (inside the api container):
    python /fwc/app/infrastructure/scripts/seed_data.py

From the host:
    make seed
"""
import logging
import os
from datetime import datetime

from adapters.farm import FarmAdaptor
from adapters.sensor import SensorAdaptor
from adapters.sensor_record import SensorRecordAdaptor
from adapters.tree import TreeAdaptor
from adapters.users import UserAdaptor
from adapters.water_source import WaterSourceAdaptor
from adapters.water_switcher import WaterSwitcherAdaptor
from adapters.zone import ZoneAdaptor
from adapters.zone_sensors import ZoneSensorsAdaptor
from config.settings import settings
from infrastructure.repositories.farm import FarmDBRepository
from infrastructure.repositories.sensor import SensorDBRepository
from infrastructure.repositories.sensor_record import SensorRecordDBRepository
from infrastructure.repositories.tree import TreeDBRepository
from infrastructure.repositories.users import UserDBRepository
from infrastructure.repositories.water_source import WaterSourceDBRepository
from infrastructure.repositories.water_switcher import WaterSwitcherDBRepository
from infrastructure.repositories.zone import ZoneDBRepository
from infrastructure.repositories.zone_sensors import ZoneSensorsDBRepository
from interfaces.api.helpers.auth import AuthHelper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("seed")

farm_repo = FarmDBRepository(uri=settings.DATABASE.URI)
zone_repo = ZoneDBRepository(uri=settings.DATABASE.URI)
sensor_repo = SensorDBRepository(uri=settings.DATABASE.URI)
water_source_repo = WaterSourceDBRepository(uri=settings.DATABASE.URI)
water_switcher_repo = WaterSwitcherDBRepository(uri=settings.DATABASE.URI)
zone_sensors_repo = ZoneSensorsDBRepository(uri=settings.DATABASE.URI)
sensor_record_repo = SensorRecordDBRepository(uri=settings.DATABASE.URI)
tree_repo = TreeDBRepository(uri=settings.DATABASE.URI)
user_repo = UserDBRepository(uri=settings.DATABASE.URI)

FARM_NAME = "Sunny Farms"
PERFORMED_BY = "seed"


def _exists(repo, attribute: str, value) -> bool:
    return bool(repo.filter([{"attribute": attribute, "value": value, "condition": "eq"}]))


def _create(repo, adaptor, data: dict, label: str, key_attr: str):
    if _exists(repo, key_attr, data[key_attr]):
        log.info("→  exists  %s (%s=%s)", label, key_attr, data[key_attr])
        return
    repo.create(adaptor.dict_to_entity({**data, "performed_by": PERFORMED_BY}))
    log.info("✓  created %s (%s=%s)", label, key_attr, data[key_attr])


def seed_farm():
    _create(farm_repo, FarmAdaptor, {
        "farm_name": FARM_NAME,
        "address": "1 Olive Lane, Tunis",
        "location": {"lat": 36.8065, "lon": 10.1815},
        "size": 12.5,
    }, "Farm", "farm_name")


def seed_admin():
    """
    Create an admin user owned by the seeded farm.

    Password from ADMIN_PASSWORD env var; defaults to 'admin123' for dev with a
    visible warning. Username/email also overridable via env.
    """
    username = os.environ.get("ADMIN_USERNAME", "admin")
    if _exists(user_repo, "username", username):
        log.info("→  exists  Admin (username=%s)", username)
        return
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        password = "admin123"
        log.warning("⚠  ADMIN_PASSWORD not set, using dev default 'admin123' (DO NOT use in prod)")
    entity = UserAdaptor.dict_to_entity({
        "username": username,
        "email": os.environ.get("ADMIN_EMAIL", f"{username}@example.com"),
        "password": AuthHelper.get_password_hash(password),
        "phone_number": "+0000000000",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "is_active": True,
        "is_superuser": True,
        "farm_name": FARM_NAME,
        "performed_by": PERFORMED_BY,
    })
    user_repo.create(entity)
    log.info("✓  created Admin (username=%s, farm=%s)", username, FARM_NAME)


def seed_zones():
    common = {
        "farm_name": FARM_NAME,
        "soil_type": "Loamy",
        "location": {"lat": 36.8065, "lon": 10.1815},
        "moisture_trigger_start": 50,
        "moisture_trigger_stop": 80,
        "saturation_trigger_start": 60,
        "saturation_trigger_stop": 90,
    }
    _create(zone_repo, ZoneAdaptor, {**common, "zone_name": "Zone A", "size": 1500},
            "Zone", "zone_name")
    _create(zone_repo, ZoneAdaptor, {**common, "zone_name": "Zone B", "size": 800},
            "Zone", "zone_name")


# Sensor serials match the Sensor Mocker's ZONES dict.
ZONE_A_TEMP = "TSN123456"
ZONE_A_MOISTURE = "MSN123456"
ZONE_A_SATURATION = "SAT123456"
ZONE_B_TEMP = "TSN123457"
ZONE_B_MOISTURE = "MSN123457"
ZONE_B_SATURATION = "SAT123457"


def seed_sensors():
    sensors = [
        ("SRC001", "source_sensor"),
        ("SWA001", "switcher_sensor"),
        ("SWB001", "switcher_sensor"),
        (ZONE_A_MOISTURE, "moisture_sensor"),
        (ZONE_A_SATURATION, "saturation_sensor"),
        (ZONE_A_TEMP, "temperature_sensor"),
        (ZONE_B_MOISTURE, "moisture_sensor"),
        (ZONE_B_SATURATION, "saturation_sensor"),
        (ZONE_B_TEMP, "temperature_sensor"),
    ]
    for serial, type_ in sensors:
        _create(sensor_repo, SensorAdaptor, {
            "serial_number": serial,
            "type": type_,
            "is_active": True,
        }, f"Sensor[{type_}]", "serial_number")


def seed_water_source():
    _create(water_source_repo, WaterSourceAdaptor, {
        "serial_number": "WS001",
        "farm_name": FARM_NAME,
        "type": "well",
        "water_pressure": 2.5,
        "water_volume": 5000.0,
        "status": "Off",
        "sensor_serial_number": "SRC001",
    }, "WaterSource", "serial_number")


def seed_water_switchers():
    for serial, zone, sensor in [
        ("SWITA01", "Zone A", "SWA001"),
        ("SWITB01", "Zone B", "SWB001"),
    ]:
        _create(water_switcher_repo, WaterSwitcherAdaptor, {
            "serial_number": serial,
            "status": "Off",
            "water_source_serial_number": "WS001",
            "zone_name": zone,
            "sensor_serial_number": sensor,
        }, "WaterSwitcher", "serial_number")


def seed_zone_sensors():
    links = [
        ("Zone A", ZONE_A_MOISTURE),
        ("Zone A", ZONE_A_SATURATION),
        ("Zone A", ZONE_A_TEMP),
        ("Zone B", ZONE_B_MOISTURE),
        ("Zone B", ZONE_B_SATURATION),
        ("Zone B", ZONE_B_TEMP),
    ]
    for zone, sensor in links:
        # ZoneSensors uses sensor_serial_number as effective unique key
        _create(zone_sensors_repo, ZoneSensorsAdaptor, {
            "zone_name": zone,
            "sensor_serial_number": sensor,
        }, "ZoneSensors", "sensor_serial_number")


def seed_trees():
    trees = [
        ("TREEA001", "Zone A", "olive", 4.2, 3.5, 18.0, "2018-04-12"),
        ("TREEA002", "Zone A", "olive", 3.8, 3.0, 15.0, "2019-03-22"),
        ("TREEA003", "Zone A", "olive", 4.5, 3.7, 19.0, "2017-05-08"),
        ("TREEB001", "Zone B", "fig", 2.5, 2.0, 8.0, "2021-02-15"),
        ("TREEB002", "Zone B", "fig", 2.8, 2.2, 10.0, "2020-09-30"),
    ]
    for serial, zone, variety, height, width, trunk, planted in trees:
        _create(tree_repo, TreeAdaptor, {
            "serial_number": serial,
            "zone_name": zone,
            "variety": variety,
            "height": height,
            "width_diameter": width,
            "trunk_diameter": trunk,
            "planting_date": planted,
        }, f"Tree[{variety}]", "serial_number")


def seed_initial_records():
    """
    Initial readings:
      Zone A: moisture=20, saturation=30  → BELOW start triggers → flow runner irrigates
      Zone B: moisture=70, saturation=80  → ABOVE start, BELOW stop → flow runner idle
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    readings = [
        (ZONE_A_MOISTURE, "moisture", 20),
        (ZONE_A_SATURATION, "saturation", 30),
        (ZONE_A_TEMP, "temperature", 24),
        (ZONE_B_MOISTURE, "moisture", 70),
        (ZONE_B_SATURATION, "saturation", 80),
        (ZONE_B_TEMP, "temperature", 22),
    ]
    for serial, type_, value in readings:
        entity = SensorRecordAdaptor.dict_to_entity({
            "sensor_serial_number": serial,
            "data": {"type": type_, "value": value, "timestamp": timestamp},
            "performed_by": PERFORMED_BY,
        })
        sensor_record_repo.create(entity)
        log.info("✓  recorded %s = %s for %s", type_, value, serial)


def main():
    log.info("--- Farm ---");
    seed_farm()
    log.info("--- Admin ---");
    seed_admin()
    log.info("--- Zones ---");
    seed_zones()
    log.info("--- Sensors ---");
    seed_sensors()
    log.info("--- WaterSource ---");
    seed_water_source()
    log.info("--- WaterSwitchers ---");
    seed_water_switchers()
    log.info("--- ZoneSensors ---");
    seed_zone_sensors()
    log.info("--- Trees ---");
    seed_trees()
    log.info("--- Initial records ---");
    seed_initial_records()
    log.info("\nSeed complete. Watch the flow runner: docker logs -f tilthwave-flow-runner")


if __name__ == "__main__":
    main()
