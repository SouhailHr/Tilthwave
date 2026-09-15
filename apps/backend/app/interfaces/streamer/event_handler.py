import logging

from adapters.sensor_record import SensorRecordAdaptor
from core.use_cases.exceptions import UseCaseException
from wiring import api_use_cases

use_cases = api_use_cases()  # Null Object broker: the streamer records state, it never commands the field
logger = logging.getLogger(__name__)


class EventHandler:
    """
    Applies the events read from the sensors topic to the database.

    Dispatch is table driven (event type -> handler, actuator type -> use case), like
    SensorCrudHelper: adding an event type is one entry, not another if-branch.
    """

    @classmethod
    def extract_event_type(cls, event):
        event_type = event.get("event_type")
        if event_type is None:
            raise UseCaseException(class_name=cls.__name__, message="Payload missing event type")
        return event_type

    @classmethod
    def _save_records(cls, event):
        """
        this method save sensor records from an event
        @param event:
        @return:
        """
        record_entity = SensorRecordAdaptor.dict_to_entity({**event, "performed_by": "streamer"})
        use_cases.sensor_record.create(entity=record_entity)

    @classmethod
    def _handle_reading(cls, event):
        """
        Method that handles the data_record events: save the record, nothing else
        """
        event.pop("event_type")
        cls._save_records(event=event)

    @classmethod
    def _handle_commanding(cls, event):
        """
        Method that handles the status_data events: an actuator confirmed a new status.
        Update the actuator's row, then keep the record.
        """
        event.pop("event_type")
        sensor_serial_number = event.get("sensor_serial_number")
        data = event.get("data") or {}
        status_updaters = {
            "switcher": use_cases.water_switcher.update_by_sensor_serial_number,
            "source": use_cases.water_source.update_by_sensor_serial_number,
        }
        update_status = status_updaters.get(data.get("type"))
        if update_status is None:
            raise UseCaseException(
                class_name=cls.__name__, message=f"Unknown actuator type {data.get('type')!r} in status_data event"
            )
        logger.info("Updating the water %s %s status to %s", data.get("type"), sensor_serial_number, data.get("status"))
        update_status(sensor_serial_number=sensor_serial_number, data={"status": data.get("status")})
        cls._save_records(event=event)

    HANDLERS = {
        "data_record": _handle_reading.__func__,
        "status_data": _handle_commanding.__func__,
    }

    def process(self, event):
        """
        Processing the event based on the event type
        @param event:
        @raises UseCaseException: unknown or missing event type
        """
        logger.info("Processing event: %s", event)
        event_type = self.extract_event_type(event=event)
        handler = self.HANDLERS.get(event_type)
        if handler is None:
            raise UseCaseException(class_name=self.__class__.__name__, message=f"Unknown event type {event_type!r}")
        handler(type(self), event)
