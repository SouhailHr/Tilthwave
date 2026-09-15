from adapters.base import BaseAdaptor
from core.entities.zone_sensors import ZoneSensors as ZoneSensorsEntity


class ZoneSensorsAdaptor(BaseAdaptor):
    ENTITY = ZoneSensorsEntity
