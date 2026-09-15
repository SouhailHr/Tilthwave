from adapters.base import BaseAdaptor
from core.entities.sensor import Sensor as SensorEntity


class SensorAdaptor(BaseAdaptor):
    ENTITY = SensorEntity
