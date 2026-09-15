from datetime import datetime

from adapters.sensor_record import SensorRecordAdaptor
from config.settings import settings
from core.entities.zone import Zone as ZoneEntity
from core.use_cases.base import BaseUseCase
import common.constants as global_constants
from core.use_cases.exceptions import UseCaseException
from core.use_cases.irrigation_task import IrrigationTaskUseCase
from adapters.irrigation_task import IrrigationTaskAdaptor
from core.use_cases.sensor import SensorUseCase
from core.use_cases.sensor_record import SensorRecordUseCase
from core.use_cases.tree import TreeUseCase
from core.use_cases.water_source import WaterSourceUseCase
from core.use_cases.water_switcher import WaterSwitcherUseCase
from core.use_cases.zone_sensors import ZoneSensorsUseCase
import logging

logger = logging.getLogger(__name__)


class ZoneUseCase(BaseUseCase):
    ENTITY = ZoneEntity

    # Get the current datetime.
    current_datetime = datetime.now()
    # Format the datetime as per the specified format
    timestamp = current_datetime.strftime("%Y-%m-%d %H:%M")

    def __init__(self, repo,
                 irrigation_task_repo=None,
                 zone_sensors_repo=None,
                 sensor_repo=None,
                 sensor_record_repo=None,
                 water_switcher_repo=None,
                 water_source_repo=None,
                 tree_repo=None,
                 switcher_broker_repo=None,
                 source_broker_repo=None):
        """
        Initialize the use case with a repository.
        we are passing sensor_repo to handle validation
        of the sensor_type

        @param repo: Repository instance handling data operations.
        @param sensor_repo: Repository instance handling data operations for sensor entity

        """
        super().__init__(repo)
        self.source_broker_repo = source_broker_repo
        self.switcher_broker_repo = switcher_broker_repo
        self.irrigation_task_repo = irrigation_task_repo
        self.zone_sensors_repo = zone_sensors_repo
        self.sensor_repo = sensor_repo
        self.sensor_record_repo = sensor_record_repo
        self.water_switcher_repo = water_switcher_repo
        self.water_source_repo = water_source_repo
        self.tree_repo = tree_repo
        self.irrigation_task_use_case = IrrigationTaskUseCase(repo=self.irrigation_task_repo)
        self.water_switcher_use_case = WaterSwitcherUseCase(repo=self.water_switcher_repo,
                                                            sensor_repo=self.sensor_repo,
                                                            broker_repo=self.switcher_broker_repo)
        self.water_source_use_case = WaterSourceUseCase(repo=self.water_source_repo,
                                                        sensor_repo=self.sensor_repo,
                                                        sensor_record_repo=sensor_record_repo,
                                                        broker_repo=self.source_broker_repo)
        self.sensor_record_use_case = SensorRecordUseCase(repo=self.sensor_record_repo)
        self.sensor_use_case = SensorUseCase(repo=self.sensor_repo)

    @staticmethod
    def check_start_irrigation(moisture: int, saturation: int, zone):
        """
            Check if irrigation needs to be started based on the current moisture and saturation levels.

            Logic:
                1. If both the current saturation is less than or equal to the trigger saturation
                   and the current moisture is less than or equal to the trigger moisture, return True.
                2. Otherwise, return False.
                3. if the triggers doesn't exist return str error

            @param moisture: int - The current moisture level of the zone.
            @param saturation: int - The current saturation level of the zone.
            @param zone: dict - A dictionary representing the zone, which should contain the keys
             'moisture_trigger_start' and 'saturation_trigger_start'.
            @return: bool - True if irrigation needs to be started, False otherwise.
        """
        try:

            moisture_trigger_start = zone.get('moisture_trigger_start')
            saturation_trigger_start = zone.get('saturation_trigger_start')

            # Ensure moisture_trigger_start and saturation_trigger_start are not None
            if moisture_trigger_start is None or saturation_trigger_start is None:
                logger.error(f"Zone {zone.get('zone_name')} has missing triggers data.")
                return False

            return saturation <= saturation_trigger_start and moisture <= moisture_trigger_start
        except Exception as e:
            logger.error(str(e))
            return False

    @staticmethod
    def check_stop_irrigation(moisture: int, saturation: int, zone):
        """
            Check if irrigation needs to be stopped based on the current moisture and saturation levels.

            Logic:
                1. If both the current saturation is greater than or equal to the trigger saturation stop
                   and the current moisture is greater than or equal to the trigger moisture stop, return True.
                2. Otherwise, return False.
                3. if the triggers doesn't exist return str error

            @param moisture: int - The current moisture level of the zone.
            @param saturation: int - The current saturation level of the zone.
            @param zone: dict - A dictionary representing the zone, which should contain the keys
             'moisture_trigger_stop' and 'saturation_trigger_stop'.
            @return: bool - True if irrigation needs to be stopped, False otherwise.
         """
        try:
            moisture_trigger_stop = zone.get('moisture_trigger_stop')
            saturation_trigger_stop = zone.get('saturation_trigger_stop')
            # Ensure moisture_trigger_stop and saturation_trigger_stop are not None
            if moisture_trigger_stop is None or saturation_trigger_stop is None:
                logger.error(f"Zone {zone.get('zone_name')} has missing triggers data.")
                return False

            return saturation >= saturation_trigger_stop and moisture >= moisture_trigger_stop
        except Exception as e:
            logger.error(str(e))
            return False

    def get_irrigation_tasks(self, zone_name: str, task_status: str):
        """
        Retrieve the irrigation tasks by zone name and tasks status.
        Logic:
            1- Use filter to get irrigation tasks by zone_name and status = task_status
            2- Return the irrigation tasks.
            3- Return None if there is no irrigation tasks for the zone with that status
        @param zone_name: str  - The name of the zone for which to retrieve the irrigation tasks.
        @param task_status: str  - the irrigation tasks status .
        @return: The irrigation tasks with task_status for the specified zone,
        or `None` if no such tasks exists
        """
        filter_by = [
            {"attribute": "zone_name", "value": zone_name, "condition": "eq"},
            {"attribute": "status", "value": task_status, "condition": "eq"}
        ]
        tasks = self.irrigation_task_use_case.filter(filters=filter_by)
        if tasks:
            return tasks

    def get_all_irrigation_tasks(self, task_status: str):
        """
        Retrieve all the irrigation tasks by tasks status.
        Logic:
            1- Use filter to all the irrigation tasks by tasks status. and status = task_status
            2- Return all the irrigation tasks.
            3- Return None if there is no irrigation tasks for the zone with that status
        @param task_status: str  - the irrigation tasks status .
        @return: all the irrigation tasks with task_status,
        or `None` if no such tasks exists
        """
        filter_by = [
            {"attribute": "status", "value": task_status, "condition": "eq"}
        ]
        tasks = self.irrigation_task_use_case.filter(filters=filter_by)
        if tasks:
            return tasks

    def start_irrigation(self, zone_name: str):
        """
            A method that start an irrigation Task for a given Zone
        Logic:
            1- Create an Irrigation Task
            2- Open the water Switcher
        @param zone_name:
        @return:
        """
        data = {
            "zone_name": zone_name,
            "status": global_constants.IRRIGATION_TASK_IN_PROGRESS,
        }
        task_entity = IrrigationTaskAdaptor.dict_to_entity(data)
        # Create an irrigation task for the zone
        task = self.irrigation_task_use_case.create(entity=task_entity)
        # start zone water switchers
        self._open_water_switchers(zone_name=zone_name)
        return task

    def stop_irrigation(self, task_in_progress):
        """
        Stops an irrigation task in progress for a given zone.
        This method updates the status of an ongoing irrigation task to 'completed'
        and records the duration of the task.
        @param task_in_progress: An object representing the irrigation task that is currently in progress.
        @return: None
        """

        task_id = task_in_progress.id
        # get task in progress duration
        duration = self.irrigation_task_use_case.get_task_in_progress_duration(task_in_progress=task_in_progress)
        data = {
            "status": global_constants.IRRIGATION_TASK_COMPLETED,
            "duration": duration
        }
        self.irrigation_task_use_case.update(id=task_id, data=data)
        self._stop_water_switchers(zone_name=task_in_progress.zone_name)

    def get_zone_sensors(self, zone_name: str):
        """
         This method gets all sensors of a specific zone by the zone name
         logic :
            1- get all the entities of zone_sensors and save them in result
            2- Add the sensor type to the actual result using the sensor repo
            3- make a dict that has { key: sensor.type : value : sensor.serial_number }
            3- if results in none raise an exception
        @param zone_name: str representing a zone by its name
        @return:  dict { key: sensor.type : value : sensor.serial_number }
        """

        filter_by = [{
            "attribute": "zone_name",
            "value": zone_name,
            "condition": "eq"
        }]
        zone_sensors_use_case = ZoneSensorsUseCase(repo=self.zone_sensors_repo, sensor_repo=self.sensor_repo)
        sensors_data = zone_sensors_use_case.filter(filters=filter_by)
        sensors = {self.sensor_use_case.get_sensor_type_by_serial_number(
            sensor_data.sensor_serial_number): sensor_data.sensor_serial_number for sensor_data in sensors_data}
        return sensors

    def get_latest_zone_data(self, zone_name: str):
        """
         This method gets the zone latest sensor records
        @param zone_name: str representing a zone by its name
        @return: List of dict of type and value ,
        eg :
        [{"type": "saturation","value": 20,}, {"type": "moisture","value": 30,}]
        """
        records = []
        sensors = self.get_zone_sensors(zone_name)
        # use the method that gets the sensor last record by serial number from sensor_records
        for sensor_type, sensor_serial_number in sensors.items():
            record = self.sensor_record_use_case.get_latest_senor_record_by_serial_number(sensor_serial_number)
            if record:
                records.append(record)
        return records

    def get_zone_water_switchers(self, zone_name: str):
        """
         This method gets all water switchers of a specific zone by the zone name
         logic :
            1- get all the entities of water switchers
            2- extract only the serial_numbers from water switchers data and return water switchers list
            3- if results in none raise an exception
        @param zone_name: str representing a zone by its name
        @return: list of water switchers serial numbers
        """
        filter_by = [{
            "attribute": "zone_name",
            "value": zone_name,
            "condition": "eq"
        }]

        water_switchers_data = self.water_switcher_use_case.filter(filters=filter_by)
        return water_switchers_data if water_switchers_data else []

    def _open_water_source(self, water_switcher):
        """
        this method opens the water source for linked water_switcher
        @param water_switcher:
        @return:
        """
        try:
            filter_by = [
                {"attribute": "serial_number", "value": water_switcher.water_source_serial_number, "condition": "eq"},
            ]

            # here it will be a list of just one water source
            # because the switcher can be linked to only one water source
            water_sources = self.water_source_use_case.filter(filters=filter_by)
            water_source = water_sources[0]
            # set the water source  status to ON
            if water_source.status == global_constants.STATUS_OFF:
                command_data_water_source = {
                    "sensor_serial_number": water_source.sensor_serial_number,
                    "data":
                        {
                            "type": "source",
                            "status": global_constants.STATUS_ON,  # operational status
                            "timestamp": self.timestamp
                        },
                }
                self.water_source_use_case.send_event(topic=settings.STREAMER.WATER_CONTROL_TOPIC,
                                                      key="water_control_data",
                                                      payload=command_data_water_source)

        except Exception as e:
            logger.error(str(e))

    def _open_water_switchers(self, zone_name: str):
        """
        This method open water switchers of a specific zone and create records for the water switcher
        @param zone_name: str representing a zone by its name
        @return:
        """
        try:
            water_switchers = self.get_zone_water_switchers(zone_name=zone_name)
            # set the water switchers  status to ON
            for water_switcher in water_switchers:
                self._open_water_source(water_switcher=water_switcher)
                command_data_water_switcher = {
                    "sensor_serial_number": water_switcher.sensor_serial_number,
                    "data":
                        {"type": "switcher",
                         "status": global_constants.STATUS_ON,
                         }
                }

                self.water_switcher_use_case.send_event(topic=settings.STREAMER.WATER_CONTROL_TOPIC,
                                                        key="water_control_data",
                                                        payload=command_data_water_switcher)
        except Exception as e:
            logger.error(str(e))

    def _stop_water_switchers(self, zone_name: str):
        """
        This method stops water switchers of a specific zone and create records for the water switcher
        @param zone_name: str representing a zone by its name
        @return:
        """
        try:
            water_switchers = self.get_zone_water_switchers(zone_name=zone_name)
            # set the water switchers  status to ON
            for water_switcher in water_switchers:
                command_data_water_switcher = {
                    "sensor_serial_number": water_switcher.sensor_serial_number,
                    "data":
                        {"type": "switcher",
                         "status": global_constants.STATUS_OFF,
                         }
                }

                self.water_switcher_use_case.send_event(topic=settings.STREAMER.WATER_CONTROL_TOPIC,
                                                        key="water_control_data",
                                                        payload=command_data_water_switcher)
        except Exception as e:
            logger.error(str(e))

    def get_zone_trees(self, zone_name: str):
        """
         This method gets all trees of a specific zone by the zone name
         logic :
            1- get all the entities of trees
        @param zone_name: str representing a zone by its name
        @return: list of trees
        """
        filter_by = [{
            "attribute": "zone_name",
            "value": zone_name,
            "condition": "eq"
        }]
        tree_use_case = TreeUseCase(repo=self.tree_repo)
        trees = tree_use_case.filter(filters=filter_by)
        return trees if trees else []

    def get_zone_data(self, zone_name: str):
        """
         This method gets the zone latest 10 sensor records for moisture and saturation
        @param zone_name: str representing a zone by its name
        @return: dict of data ,
        eg :
        """
        data_chart = {}
        sensors = self.get_zone_sensors(zone_name)
        # use the method that gets the sensor last record by serial number from sensor_records
        for sensor_type, sensor_serial_number in sensors.items():
            records = self.sensor_record_use_case.get_get_sensor_records(sensor_serial_number)
            for record in records[:15]:
                data = record.data
                timestamp = data['timestamp']
                time = timestamp[:16]

                # Check if the record contains moisture or saturation
                if 'moisture' in data['type'] or 'saturation' in data['type']:
                    # Create a dictionary containing moisture and saturation values
                    value = {}
                    if 'moisture' in data['type']:
                        value['Moist'] = data['value']
                    if 'saturation' in data['type']:
                        value['Saturation'] = data['value']

                    # Check if the time already exists in the data_chart dictionary
                    if time in data_chart:
                        # If it does, update the existing entry
                        data_chart[time].update(value)
                    else:
                        # If not, add a new entry with the time as key and the value dictionary as value
                        data_chart[time] = value

        return data_chart

    def get_stats(self, name: str):
        """
         This method gets the stats per zone
        @param name: str represents the zone
        @return: stats_dict
        eg:
            stats ={
            "total_water_switchers": 8,
             "total_sensors": 123,
             "total_trees": 123,
             "total_irrigation_tasks": 3,
            }
        """
        zone_data = self.get_zone_data(zone_name=name)
        sorted_zone_data = dict(sorted(zone_data.items()))
        # We check if the irrigation_tasks_in_progress is None or not
        if self.get_irrigation_tasks(
                zone_name=name,
                task_status=global_constants.IRRIGATION_TASK_IN_PROGRESS) is None:
            irrigation_tasks_in_progress = 0
        else:
            irrigation_tasks_in_progress = len(self.get_irrigation_tasks(
                zone_name=name,
                task_status=global_constants.IRRIGATION_TASK_IN_PROGRESS))

        # We check if the irrigation_tasks_in_completed is None or not
        if self.get_irrigation_tasks(
                zone_name=name,
                task_status=global_constants.IRRIGATION_TASK_COMPLETED) is None:
            irrigation_tasks_completed = 0
        else:
            irrigation_tasks_completed = len(self.get_irrigation_tasks(
                zone_name=name,
                task_status=global_constants.IRRIGATION_TASK_COMPLETED))

        stats_dict = {
            "total_trees": len(self.get_zone_trees(zone_name=name)),
            "total_irrigation_tasks_completed": irrigation_tasks_completed,
            "total_irrigation_tasks_in_progress": irrigation_tasks_in_progress,
            "chartData": sorted_zone_data
        }

        return stats_dict
