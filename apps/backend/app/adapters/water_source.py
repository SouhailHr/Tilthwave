from adapters.base import BaseAdaptor
from core.entities.water_source import WaterSource as WaterSourceEntity


class WaterSourceAdaptor(BaseAdaptor):
    ENTITY = WaterSourceEntity
