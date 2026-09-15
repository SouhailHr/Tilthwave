from adapters.base import BaseAdaptor
from core.entities.sensor_record import SensorRecord as SensorRecordEntity


class SensorRecordAdaptor(BaseAdaptor):
    ENTITY = SensorRecordEntity
