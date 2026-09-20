from sqlalchemy import Boolean, Column, ForeignKey, String

from infrastructure.database.tables.base import TilthwaveBaseModel


class Sensor(TilthwaveBaseModel):
    """
    Sensor model for storing Sensor information.
    """

    __tablename__ = "sensor"

    type = Column(
        String(100),
        nullable=False,
        comment="Type of the sensor (e.g., switcher_sensor, water_source_sensor, temperature_sensor, "
        "moisture_sensor, saturation_sensor)",
    )
    is_active = Column(
        Boolean, default=True, nullable=False, comment="General status of the sensor (e.g., active, inactive)"
    )

    serial_number = Column(String(50), nullable=False, unique=True, comment="Unique serial number of the sensor")

    # Tenant linkage: the farm that registered the sensor. Set by BaseDBRepo._bind_tenant from the
    # caller's token, never from the request body (revision b2d3e4f5a6c7 backfilled existing rows).
    farm_name = Column(
        String(100),
        ForeignKey("farm.farm_name", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Foreign key referencing the farm that owns the sensor.",
    )

    # Relationships
