def _pattern(values) -> str:
    """The regex a pydantic `pattern=` field takes for an exact match of one of `values`."""
    return "^(" + "|".join(values) + ")$"


# operational status : water source , water switcher
STATUS_ON = "On"
STATUS_OFF = "Off"
ACTUATOR_STATUSES = (STATUS_ON, STATUS_OFF, "Error")
WATER_SWITCHER_STATUS = _pattern(ACTUATOR_STATUSES)
WATER_SOURCE_STATUS = _pattern(ACTUATOR_STATUSES)

# Sensor Constants
SOURCE_SENSOR = "source_sensor"
SWITCHER_SENSOR = "switcher_sensor"
ZONE_SENSORS = ["temperature_sensor", "moisture_sensor", "saturation_sensor"]
SENSOR_TYPE_LIST = (SWITCHER_SENSOR, SOURCE_SENSOR, *ZONE_SENSORS)
SENSOR_TYPES = _pattern(SENSOR_TYPE_LIST)

# USER CONSTANTS
USER_ROLES_LIST = ["admin", "owner", "worker", "engineer"]
SUPERUSER_ROLES = ["admin", "owner"]
USER_ROLES = _pattern(USER_ROLES_LIST)

# Irrigation Task Constants
IRRIGATION_TASK_IN_PROGRESS = "in progress"
IRRIGATION_TASK_COMPLETED = "completed"
IRRIGATION_TASK_STATUSES = ("pending", IRRIGATION_TASK_IN_PROGRESS, IRRIGATION_TASK_COMPLETED, "canceled")
IRRIGATION_TASK_STATUS = _pattern(IRRIGATION_TASK_STATUSES)

# Permissions
# role-based access control (RBAC) structure

# Two profiles: admins and owners manage the farm; workers and engineers observe it (and may
# update a tree, e.g. its measurements). Every role reaches its own profile through /account.
_MANAGE = {
    "users": ["read", "write", "update", "delete"],
    "farms": ["read", "write", "update", "delete"],
    "sensors": ["read", "write", "update", "delete"],
    "zones": ["read", "write", "update", "delete"],
    "water-switchers": ["read", "write", "update", "delete"],
    "water-sources": ["read", "write", "update", "delete"],
    "zone-sensors": ["read", "write", "update", "delete"],
    "irrigation-tasks": ["read", "write", "update", "delete"],
    "sensor-records": ["read"],
    "trees": ["read", "write", "update", "delete"],
    "dashboard": ["read"],
    "account": ["read", "write", "update"],
}
_OBSERVE = {
    # No "users": the staff list (email, phone, name of every colleague) is for admins and owners.
    "farms": ["read"],
    "sensors": ["read"],
    "zones": ["read"],
    "water-switchers": ["read"],
    "water-sources": ["read"],
    "zone-sensors": ["read"],
    "irrigation-tasks": ["read"],
    "sensor-records": ["read"],
    "trees": ["read", "update"],
    "dashboard": ["read"],
    "account": ["read", "write", "update"],
}
RESOURCES_FOR_ROLES = {"admin": _MANAGE, "owner": _MANAGE, "worker": _OBSERVE, "engineer": _OBSERVE}

# Excluded paths from permission
EXCLUDED_PATHS = ["auth", "docs", "openapi.json", "health"]
