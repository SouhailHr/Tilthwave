from common import constants as global_constants
from core.entities.water_switcher import WaterSwitcher as WaterSwitcherEntity
from core.use_cases.actuator import ActuatorUseCase


class WaterSwitcherUseCase(ActuatorUseCase):
    ENTITY = WaterSwitcherEntity
    SENSOR_TYPE = global_constants.SWITCHER_SENSOR
    NOUN = "water switcher"
