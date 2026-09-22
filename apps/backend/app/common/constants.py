# operational status : water source , water switcher
STATUS_ON = "On"
STATUS_OFF = "Off"

# Sensor Constants
SENSOR_TYPES = "^(switcher_sensor|source_sensor|temperature_sensor|moisture_sensor|saturation_sensor)$"
SOURCE_SENSOR = "source_sensor"
SWITCHER_SENSOR = "switcher_sensor"
ZONE_SENSORS = ["temperature_sensor", "moisture_sensor", "saturation_sensor"]

# Water Switcher Constants

WATER_SWITCHER_STATUS = "^(On|Off|Error)$"

# Water source Constants

WATER_SOURCE_STATUS = "^(On|Off|Error)$"


# USER CONSTANTS

USER_ROLES = "^(admin|owner|worker|engineer)$"
SUPERUSER_ROLES = ["admin", "owner"]
USER_ROLES_LIST = ["admin", "owner", "worker", "engineer"]

# Irrigation Task Constants
IRRIGATION_TASK_STATUS = "^(pending|in progress|completed|canceled)$"
IRRIGATION_TASK_IN_PROGRESS = "in progress"
IRRIGATION_TASK_COMPLETED = "completed"

# Permissions
# role-based access control (RBAC) structure

RESOURCES_FOR_ROLES = {
    "admin": {
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
        # Own profile and password (interfaces/api/endpoints/account.py): every role, self only.
        "account": ["read", "write", "update"],
    },
    "owner": {
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
        # Own profile and password (interfaces/api/endpoints/account.py): every role, self only.
        "account": ["read", "write", "update"],
    },
    "worker": {
        "users": ["read"],
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
        # Own profile and password (interfaces/api/endpoints/account.py): every role, self only.
        "account": ["read", "write", "update"],
    },
    "engineer": {
        "users": ["read"],
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
        # Own profile and password (interfaces/api/endpoints/account.py): every role, self only.
        "account": ["read", "write", "update"],
    },
}

# Excluded paths from permission
EXCLUDED_PATHS = ["auth", "docs", "openapi.json", "health"]
