from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from infrastructure.database.tables.base import TilthwaveBaseModel
from infrastructure.database.tables.sensor import Sensor
from infrastructure.database.tables.zone import Zone


class ZoneSensors(TilthwaveBaseModel):
    """
    ZoneSensors model for storing the sensors of each zone information.
    """

    __tablename__ = "zone_sensors"  # Between table for zone and sensors to handle the Many-To-Many relationship

    sensor_serial_number = Column(
        String,
        ForeignKey("sensor.serial_number", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=True,
        unique=True,
        comment="Foreign key referencing the sensor's serial_number",
    )
    zone_name = Column(
        String,
        ForeignKey("zone.zone_name", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=True,
        comment="Foreign key referencing the zone's name",
    )

    # Relationships

    # Many-to-One relationship with Sensor. A ZoneSensors can have multiple Sensors.
    sensor = relationship(Sensor)

    # Many-to-One relationship with Zone. A ZoneSensors can have multiple Zones.
    zone = relationship(Zone)
