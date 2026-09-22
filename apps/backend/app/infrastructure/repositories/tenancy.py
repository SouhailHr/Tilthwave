"""
How a table maps to the caller's farm: one object that both filters reads and binds writes, so
a scope kind cannot exist on one side only (which is exactly how a farm-scoped owner once got to
create rows under another farm's name).

    TenantScope.column("farm_name")   the row names its farm in a column
    TenantScope.own("farm_name")      the row IS the farm (the farm table)
    TenantScope.via_zone()            the row names a zone; the zone names the farm
    TenantScope.via_sensor()          the row names a sensor; the sensor names the farm

The repository calls apply()/bind() only for an HTTP caller with a farm (see BaseDBRepo).
"""

from common.exceptions import NotFoundError
from infrastructure.database.tables.sensor import Sensor
from infrastructure.database.tables.zone import Zone


class TenantScope:
    COLUMN, OWN, VIA_ZONE, VIA_SENSOR = "column", "own", "via_zone", "via_sensor"

    def __init__(self, kind: str, column: str | None = None):
        self.kind = kind
        self.column = column

    @classmethod
    def column(cls, name: str) -> "TenantScope":
        return cls(cls.COLUMN, name)

    @classmethod
    def own(cls, name: str) -> "TenantScope":
        return cls(cls.OWN, name)

    @classmethod
    def via_zone(cls) -> "TenantScope":
        return cls(cls.VIA_ZONE)

    @classmethod
    def via_sensor(cls) -> "TenantScope":
        return cls(cls.VIA_SENSOR)

    def __repr__(self) -> str:
        return f"TenantScope({self.kind}{', ' + self.column if self.column else ''})"

    # ---- reads -----------------------------------------------------------------------------

    def apply(self, query, model, farm: str, session):
        """Restrict `query` over `model` to the rows of `farm`."""
        if self.kind in (self.COLUMN, self.OWN):
            return query.filter(getattr(model, self.column) == farm)
        if self.kind == self.VIA_ZONE:
            owned = session.query(Zone.zone_name).filter(Zone.farm_name == farm)
            return query.filter(model.zone_name.in_(owned))
        if self.kind == self.VIA_SENSOR:
            owned = session.query(Sensor.serial_number).filter(Sensor.farm_name == farm)
            return query.filter(model.sensor_serial_number.in_(owned))
        raise ValueError(f"unknown tenant scope kind {self.kind!r}")

    # ---- writes ----------------------------------------------------------------------------

    def bind(self, data: dict, model, farm: str, session) -> dict:
        """
        Make a row being written belong to `farm`. A farm column is forced to the caller's farm
        (for the farm table itself that means a farm-scoped caller can only "create" their own
        farm, which the unique name turns into a 409). A referenced zone or sensor must be one of
        the caller's, otherwise NotFoundError: it is invisible to them, so "not found", not
        "forbidden"; without this a tenant could register a tree, switcher, task or reading in
        another farm's zone or sensor.
        """
        if self.kind in (self.COLUMN, self.OWN):
            data[self.column] = farm
        elif self.kind == self.VIA_ZONE and data.get("zone_name") is not None:
            owned = session.query(Zone.id).filter(Zone.zone_name == data["zone_name"], Zone.farm_name == farm).first()
            if owned is None:
                raise NotFoundError("Zone not found")
        elif self.kind == self.VIA_SENSOR and data.get("sensor_serial_number") is not None:
            owned = (
                session.query(Sensor.id)
                .filter(Sensor.serial_number == data["sensor_serial_number"], Sensor.farm_name == farm)
                .first()
            )
            if owned is None:
                raise NotFoundError("Sensor not found")
        elif self.kind not in (self.VIA_ZONE, self.VIA_SENSOR):
            raise ValueError(f"unknown tenant scope kind {self.kind!r}")
        return data
