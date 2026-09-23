from interfaces.api.endpoints.base import crud_router
from interfaces.api.endpoints.sensor_base import SensorCrudHelper
from interfaces.api.schemas.sensor import SensorCreate, SensorUpdate

# Create and update also maintain the sensor's link to its zone / switcher / source, per
# assigned_to_type, and every item carries `assigned_to` (SensorCrudHelper).
router = crud_router("/sensors", "Sensor", SensorCrudHelper, SensorCreate, SensorUpdate, noun="sensor")
