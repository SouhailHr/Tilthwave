"""
Composition root.

The one place where repositories and use cases are constructed. Interfaces (API routers,
streamer, flow runner, scripts) import from here instead of building their own graph, so:
  - every process shares one engine per database URI,
  - the broker gateway is chosen per process (real producer for the flow runner, a Null Object
    for anything that must never actuate hardware),
  - tests can build the same graph against SQLite by setting POSTGRES_URI before import.
"""

import random
from dataclasses import dataclass
from functools import cache

from config.settings import settings
from core.use_cases.farm import FarmUseCase
from core.use_cases.irrigation_task import IrrigationTaskUseCase
from core.use_cases.sensor import SensorUseCase
from core.use_cases.sensor_record import SensorRecordUseCase
from core.use_cases.tree import TreeUseCase
from core.use_cases.users import UserUseCase
from core.use_cases.water_source import WaterSourceUseCase
from core.use_cases.water_switcher import WaterSwitcherUseCase
from core.use_cases.zone import ZoneUseCase
from core.use_cases.zone_sensors import ZoneSensorsUseCase
from infrastructure.repositories.base import NoopBrokerRepo
from infrastructure.repositories.farm import FarmDBRepository
from infrastructure.repositories.irrigation_task import IrrigationTaskDBRepository
from infrastructure.repositories.sensor import SensorDBRepository
from infrastructure.repositories.sensor_record import SensorRecordDBRepository
from infrastructure.repositories.tree import TreeDBRepository
from infrastructure.repositories.users import UserDBRepository
from infrastructure.repositories.water_source import WaterSourceBrokerRepository, WaterSourceDBRepository
from infrastructure.repositories.water_switcher import WaterSwitcherBrokerRepository, WaterSwitcherDBRepository
from infrastructure.repositories.zone import ZoneDBRepository
from infrastructure.repositories.zone_sensors import ZoneSensorsDBRepository


@dataclass(frozen=True)
class Repositories:
    farm: FarmDBRepository
    zone: ZoneDBRepository
    zone_sensors: ZoneSensorsDBRepository
    sensor: SensorDBRepository
    sensor_record: SensorRecordDBRepository
    water_source: WaterSourceDBRepository
    water_switcher: WaterSwitcherDBRepository
    tree: TreeDBRepository
    irrigation_task: IrrigationTaskDBRepository
    users: UserDBRepository


@dataclass(frozen=True)
class BrokerRepositories:
    water_source: WaterSourceBrokerRepository
    water_switcher: WaterSwitcherBrokerRepository


@dataclass(frozen=True)
class UseCases:
    farm: FarmUseCase
    zone: ZoneUseCase
    zone_sensors: ZoneSensorsUseCase
    sensor: SensorUseCase
    sensor_record: SensorRecordUseCase
    water_source: WaterSourceUseCase
    water_switcher: WaterSwitcherUseCase
    tree: TreeUseCase
    irrigation_task: IrrigationTaskUseCase
    users: UserUseCase


def build_repositories(uri: str) -> Repositories:
    return Repositories(
        farm=FarmDBRepository(uri=uri),
        zone=ZoneDBRepository(uri=uri),
        zone_sensors=ZoneSensorsDBRepository(uri=uri),
        sensor=SensorDBRepository(uri=uri),
        sensor_record=SensorRecordDBRepository(uri=uri),
        water_source=WaterSourceDBRepository(uri=uri),
        water_switcher=WaterSwitcherDBRepository(uri=uri),
        tree=TreeDBRepository(uri=uri),
        irrigation_task=IrrigationTaskDBRepository(uri=uri),
        users=UserDBRepository(uri=uri),
    )


def build_noop_broker_repositories() -> BrokerRepositories:
    """Broker gateways that log and drop commands: for the API, the streamer and scripts."""
    return BrokerRepositories(water_source=NoopBrokerRepo(), water_switcher=NoopBrokerRepo())


def build_kafka_broker_repositories() -> BrokerRepositories:
    """Broker gateways publishing to Kafka: only the flow runner may actuate the field."""
    from confluent_kafka import Producer  # imported lazily: only the flow runner needs librdkafka wiring

    broker = random.choice(settings.STREAMER.BROKER_HOSTS)
    producer = Producer({"bootstrap.servers": broker})
    return BrokerRepositories(
        water_source=WaterSourceBrokerRepository(producer=producer, random_broker=broker),
        water_switcher=WaterSwitcherBrokerRepository(producer=producer, random_broker=broker),
    )


def build_use_cases(repos: Repositories, broker: BrokerRepositories) -> UseCases:
    return UseCases(
        farm=FarmUseCase(
            repo=repos.farm,
            zone_repo=repos.zone,
            water_switcher_repo=repos.water_switcher,
            water_source_repo=repos.water_source,
            tree_repo=repos.tree,
            sensor_record_repo=repos.sensor_record,
        ),
        zone=ZoneUseCase(
            repo=repos.zone,
            irrigation_task_repo=repos.irrigation_task,
            zone_sensors_repo=repos.zone_sensors,
            sensor_repo=repos.sensor,
            sensor_record_repo=repos.sensor_record,
            water_switcher_repo=repos.water_switcher,
            water_source_repo=repos.water_source,
            tree_repo=repos.tree,
            switcher_broker_repo=broker.water_switcher,
            source_broker_repo=broker.water_source,
        ),
        zone_sensors=ZoneSensorsUseCase(repo=repos.zone_sensors, sensor_repo=repos.sensor),
        sensor=SensorUseCase(
            repo=repos.sensor,
            zone_repo=repos.zone,
            zone_sensors_repo=repos.zone_sensors,
            water_source_repo=repos.water_source,
            water_switcher_repo=repos.water_switcher,
        ),
        sensor_record=SensorRecordUseCase(repo=repos.sensor_record),
        water_source=WaterSourceUseCase(
            repo=repos.water_source,
            sensor_repo=repos.sensor,
            sensor_record_repo=repos.sensor_record,
            broker_repo=broker.water_source,
        ),
        water_switcher=WaterSwitcherUseCase(
            repo=repos.water_switcher, sensor_repo=repos.sensor, broker_repo=broker.water_switcher
        ),
        tree=TreeUseCase(repo=repos.tree),
        irrigation_task=IrrigationTaskUseCase(repo=repos.irrigation_task),
        users=UserUseCase(repo=repos.users),
    )


@cache
def repositories() -> Repositories:
    return build_repositories(settings.DATABASE.URI)


@cache
def api_use_cases() -> UseCases:
    """Use cases for the API and other processes that must not send field commands."""
    return build_use_cases(repositories(), build_noop_broker_repositories())


@cache
def worker_use_cases() -> UseCases:
    """Use cases for the flow runner: field commands go to Kafka."""
    return build_use_cases(repositories(), build_kafka_broker_repositories())
