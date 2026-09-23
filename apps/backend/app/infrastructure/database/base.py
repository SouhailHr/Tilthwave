# Import all the models, so that Base has them before being imported by Alembic

from infrastructure.database.base_class import Base  # noqa: F401 pragma: no cover
from infrastructure.database.tables.farm import Farm  # noqa: F401 pragma: no cover
from infrastructure.database.tables.irrigation_task import IrrigationTask  # noqa: F401 pragma: no cover
from infrastructure.database.tables.sensor import Sensor  # noqa: F401 pragma: no cover
from infrastructure.database.tables.sensor_record import SensorRecord  # noqa: F401 pragma: no cover
from infrastructure.database.tables.tree import Tree  # noqa: F401 pragma: no cover
from infrastructure.database.tables.user_session import UserSession  # noqa: F401 pragma: no cover
from infrastructure.database.tables.users import Users  # noqa: F401 pragma: no cover
from infrastructure.database.tables.water_source import WaterSource  # noqa: F401 pragma: no cover
from infrastructure.database.tables.water_switcher import WaterSwitcher  # noqa: F401 pragma: no cover
from infrastructure.database.tables.zone import Zone  # noqa: F401 pragma: no cover
from infrastructure.database.tables.zone_sensors import ZoneSensors  # noqa: F401 pragma: no cover
