import logging
import random

from apscheduler.schedulers.background import BackgroundScheduler

import common.constants as global_constants
from adapters.irrigation_task import IrrigationTaskAdaptor
from adapters.zone import ZoneAdaptor
from config.settings import settings
from core.use_cases.irrigation_task import IrrigationTaskUseCase
from core.use_cases.water_source import WaterSourceUseCase
from core.use_cases.zone import ZoneUseCase
from infrastructure.repositories.irrigation_task import IrrigationTaskDBRepository
from infrastructure.repositories.sensor import SensorDBRepository
from infrastructure.repositories.sensor_record import SensorRecordDBRepository
from infrastructure.repositories.water_source import WaterSourceDBRepository, WaterSourceBrokerRepository
from infrastructure.repositories.water_switcher import WaterSwitcherDBRepository, WaterSwitcherBrokerRepository
from infrastructure.repositories.zone import ZoneDBRepository
from infrastructure.repositories.zone_sensors import ZoneSensorsDBRepository
from interfaces.flow_runner.helper import FlowRunnerCrudHelper
from confluent_kafka import Producer

scheduler = BackgroundScheduler()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Kafka config
# Kafka broker configuration
random_broker = random.choice(settings.STREAMER.BROKER_HOSTS)

# Create a Kafka producer
producer = Producer({"bootstrap.servers": random_broker})

# Getting all the DB repos to use in zone use case

irrigation_task_repo = IrrigationTaskDBRepository(uri=settings.DATABASE.URI)
zone_sensors_repo = ZoneSensorsDBRepository(uri=settings.DATABASE.URI)
sensor_repo = SensorDBRepository(uri=settings.DATABASE.URI)
sensor_records_repo = SensorRecordDBRepository(uri=settings.DATABASE.URI)
zone_repo = ZoneDBRepository(uri=settings.DATABASE.URI)
water_switcher_repo = WaterSwitcherDBRepository(uri=settings.DATABASE.URI)
water_source_repo = WaterSourceDBRepository(uri=settings.DATABASE.URI)

# The broker repos

water_source_broker_repo = WaterSourceBrokerRepository(producer=producer, random_broker=random_broker)
water_switcher_broker_repo = WaterSwitcherBrokerRepository(producer=producer, random_broker=random_broker)


# Getting the zones to check triggers
zone_use_case = ZoneUseCase(repo=zone_repo,
                            irrigation_task_repo=irrigation_task_repo,
                            zone_sensors_repo=zone_sensors_repo,
                            sensor_repo=sensor_repo,
                            sensor_record_repo=sensor_records_repo,
                            water_switcher_repo=water_switcher_repo,
                            water_source_repo=water_source_repo,
                            tree_repo=None,
                            switcher_broker_repo=water_switcher_broker_repo,
                            source_broker_repo=water_source_broker_repo)

irrigation_task_use_case = IrrigationTaskUseCase(repo=irrigation_task_repo)
water_source_use_case = WaterSourceUseCase(repo=water_source_repo, broker_repo=water_source_broker_repo,
                                           sensor_repo=sensor_repo,
                                           sensor_record_repo=sensor_records_repo)


class IrrigationTaskFlowRunnerHelper(FlowRunnerCrudHelper):
    ADAPTOR_CLASS = IrrigationTaskAdaptor
    USE_CASE_INSTANCE = irrigation_task_use_case


class ZoneFlowRunnerHelper(FlowRunnerCrudHelper):
    ADAPTOR_CLASS = ZoneAdaptor
    USE_CASE_INSTANCE = zone_use_case


class ZoneAutomaticIrrigationHelper:
    STOP = "stop"
    START = "start"

    @classmethod
    def _get_value_from_sensors_record(cls, sensors_records, value):
        """

        @param sensors_records:
        @param value:
        @return:
        """
        record_dict = {record['type']: record['value'] for record in sensors_records}

        # Extract the values for saturation and moisture
        return record_dict.get(value)

    @classmethod
    def start_irrigation(cls, zone):
        """
        Start an irrigation task for the Zone
        Logic:
            1- Create an Irrigation task
        @param zone: Zone data
        @return:
        """
        zone_name = zone.get('zone_name')
        logger.info(f"Starting Irrigation for  {zone_name}")
        try:
            irrigation_task = zone_use_case.start_irrigation(zone_name=zone_name)
            logger.info(f"Irrigation started id: {irrigation_task.id}")
            return irrigation_task
        except Exception as e:
            logger.error(f"Not able to start the Irrigation for {zone_name}: {str(e)}")

    @classmethod
    def stop_irrigation(cls, zone, task_to_stop):
        zone_name = zone.get('zone_name')
        logger.info(f"Stopping Irrigation for  {zone_name}")

        # stop the irrigation task for this zone
        try:
            zone_use_case.stop_irrigation(task_in_progress=task_to_stop)
        except Exception as e:
            logger.error(f"Not able to stop the Irrigation for  {zone_name}: {str(e)}")

    @classmethod
    def _check_start_stop(cls, zone, tasks_in_progress):
        """
        Method that checks if we need to start or stop irrigation
        Logic:
            1- get the zone latest data
            2- Get the zone triggers
            3- Check if the riggers mates the stop or start condition
        @zone: A dict that contains a Zone data
        @return: str STOP or START
        """
        # get the zone name and triggers
        zone_name = zone.get("zone_name")
        logger.info(f"Checking {zone_name} ........")
        # 1- get the zone latest data
        zone_sensors_records = zone_use_case.get_latest_zone_data(zone_name=zone_name)
        # zone_sensors_records is in this format:
        # [{"type": "saturation","value": 20,}, {"type": "moisture","value": 30,}....]
        current_saturation = cls._get_value_from_sensors_record(zone_sensors_records, "saturation")
        current_moisture = cls._get_value_from_sensors_record(zone_sensors_records, "moisture")
        logger.info(
            f"Current values for {zone_name} :  Moisture = {current_moisture} | Saturation = {current_saturation} ")
        # Ensure current_saturation and current_moisture are not None
        if current_saturation is None or current_moisture is None:
            logger.error(f"Zone {zone_name} has missing sensor data.")
            return None

        # Start conditions :
        if tasks_in_progress is None and zone_use_case.check_start_irrigation(moisture=current_moisture,
                                                                              saturation=current_saturation,
                                                                              zone=zone):
            return cls.START
        if tasks_in_progress and zone_use_case.check_stop_irrigation(moisture=current_moisture,
                                                                     saturation=current_saturation,
                                                                     zone=zone):
            return cls.STOP

    @classmethod
    def auto_irrigation(cls):
        """
        this method is used to check_triggers of start and stop in each zone, so it starts irrigation
        and stops it when needed also creating the irrigation task and updating the status to completed
        when the variables of zone of an irrigation task in progress is reached the stop triggers

        Logic;
            - For each zone we check if Irrigation need to be started or stop it
        @return:
        """
        # get all zones
        zones = ZoneFlowRunnerHelper.get_all()

        # TODO ADD FIELD IN Zone auto_irrigated : bool , To handle hard stop from user
        # TODO ADD logic for opening and closing water source 
        for zone in zones:
            # Check if zone has irrigation task in progress
            tasks_in_progress = zone_use_case.get_irrigation_tasks(
                zone_name=zone.get("zone_name"),
                task_status=global_constants.IRRIGATION_TASK_IN_PROGRESS)

            condition = cls._check_start_stop(zone, tasks_in_progress)
            if condition == cls.START:
                cls.start_irrigation(zone=zone)
            elif condition == cls.STOP:
                cls.stop_irrigation(zone=zone, task_to_stop=tasks_in_progress[0])
            else:
                continue
        # get all irrigation tasks in progress
        all_irrigation_tasks_in_progress = zone_use_case.get_all_irrigation_tasks(
            task_status=global_constants.IRRIGATION_TASK_IN_PROGRESS)

        if all_irrigation_tasks_in_progress is None:
            logger.info(f'Closing all the water sources')
            water_source_use_case.close_all_water_sources()


if __name__ == "__main__":
    logger.debug(f"................ Starting Flow Runner ......... ")

    scheduler.add_job(ZoneAutomaticIrrigationHelper.auto_irrigation, 'interval',
                      minutes=settings.FLOW_RUNNER.MINUTES)  # Check triggers every 1 minutes
    scheduler.start()

    try:
        while True:
            pass  # Infinite loop to keep the script running
    except KeyboardInterrupt:
        scheduler.shutdown()
