import logging

from config.settings import settings
from core.use_cases.sensor_record import SensorRecordUseCase
from core.use_cases.water_source import WaterSourceUseCase
from core.use_cases.water_switcher import WaterSwitcherUseCase
from infrastructure.repositories.sensor_record import SensorRecordDBRepository
from infrastructure.repositories.water_source import WaterSourceDBRepository
from infrastructure.repositories.water_switcher import WaterSwitcherDBRepository
from adapters.sensor_record import SensorRecordAdaptor

# Db repos
sensor_record_repo = SensorRecordDBRepository(uri=settings.DATABASE.URI)
water_source_repo = WaterSourceDBRepository(uri=settings.DATABASE.URI)
water_switcher_repo = WaterSwitcherDBRepository(uri=settings.DATABASE.URI)

# Use cases
sensor_record_use_case = SensorRecordUseCase(repo=sensor_record_repo)
water_source_use_case = WaterSourceUseCase(repo=water_source_repo, sensor_repo=None, sensor_record_repo=None,
                                           broker_repo=None)
water_switcher_use_case = WaterSwitcherUseCase(repo=water_switcher_repo, sensor_repo=None)

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)


class EventHandler:
    """
    A class for handling the events.
    """

    @classmethod
    def extract_event_type(cls, event):
        event_type = event.get("event_type")
        if event_type is None:
            raise Exception("Payload missing event type")
        return event_type

    @classmethod
    def _save_records(cls, event):
        """
        this method save sensor records from an event
        @param event:
        @return:
        """
        # add the performer as the streamer
        # logger.info("***** Saving the record *****")
        record_entity = SensorRecordAdaptor.dict_to_entity(event)
        sensor_record_use_case.create(entity=record_entity)
        # logger.info("***** Record Saved Successfully *****")

    @classmethod
    def _handle_reading(cls, event):
        """
        Method that handel the data_record events
        @return:
        """
        # Save the records without any other handling
        event.pop("event_type")
        cls._save_records(event=event)

    @classmethod
    def _handle_commanding(cls, event):
        """
        Method that handel the reading events
        @return:
        """
        event.pop("event_type")
        sensor_serial_number = event.get("sensor_serial_number")
        data = event.get("data")
        status = data.get("status")
        if data.get("type") == "switcher":
            # Update water switcher status
            logger.info("***** Updating the water switcher status *****")
            water_switcher_use_case.update_by_sensor_serial_number(sensor_serial_number=sensor_serial_number,
                                                                   data={"status": status})
        if data.get("type") == "source":
            # Update water source status
            logger.info("***** Updating the water source status *****")
            water_source_use_case.update_by_sensor_serial_number(sensor_serial_number=sensor_serial_number,
                                                                 data={"status": status})
        # Save records after handling the status
        cls._save_records(event=event)

    def process(self, event):
        """
        Processing the event based on the event type
        @param event:
        @return:
        """
        # 1- get event type
        logger.info(f"***** Processing event ***** : {event}")
        try:
            event_type = self.extract_event_type(event=event)
            if event_type == "data_record":
                self._handle_reading(event=event)
            if event_type == "status_data":
                self._handle_commanding(event=event)

        except Exception as e:
            raise e
