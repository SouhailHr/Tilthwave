from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from infrastructure.database.tables.base import TilthwaveBaseModel
from infrastructure.database.tables.sensor import Sensor
from infrastructure.database.tables.water_source import WaterSource
from infrastructure.database.tables.zone import Zone


class WaterSwitcher(TilthwaveBaseModel):
    """
    WaterSwitcher model for storing WaterSwitcher information.
    """

    __tablename__ = "water_switcher"

    status = Column(
        String, nullable=False, comment='Operational status of the water switcher (e.g., "on", "off", "error").'
    )
    water_source_serial_number = Column(
        String,
        ForeignKey("water_source.serial_number", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
        comment="Foreign key linking to the Water Source table. "
        "Indicates the source from which the switcher draws water.",
    )

    sensor_serial_number = Column(
        String,
        ForeignKey("sensor.serial_number", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        comment="Foreign key linking to a specific Sensor.",
    )
    zone_name = Column(
        String,
        ForeignKey("zone.zone_name", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
        comment="Foreign key referencing the zone's name",
    )
    serial_number = Column(
        String(50), nullable=False, unique=True, comment="Unique serial number of the water switcher"
    )

    # Relationships

    # One-to-one relationship with the Sensor model. Each water switcher is controlled by one sensor
    sensor = relationship(Sensor)

    # Many-to-one relationship with the Zone model. Each Zone is controlled by Many water switchers
    zone = relationship(Zone)

    # One-To-Many Relationship to the Water Source model. Each water source can have multiple switchers
    water_source = relationship(WaterSource)
