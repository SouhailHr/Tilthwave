from adapters.base import BaseAdaptor
from core.entities.water_switcher import WaterSwitcher as WaterSwitcherEntity


class WaterSwitcherAdaptor(BaseAdaptor):
    ENTITY = WaterSwitcherEntity
