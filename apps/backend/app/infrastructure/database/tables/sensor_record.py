from sqlalchemy import JSON, Column, ForeignKey, Index, String, text
from sqlalchemy.orm import relationship

# To avoid potential complications with import order and circular dependencies.
# such as mappers failing to initialize because they can't locate related classes during their configuration.
from infrastructure.database.tables.base import TilthwaveBaseModel
from infrastructure.database.tables.sensor import Sensor


class SensorRecord(TilthwaveBaseModel):
    """
    SensorRecordModel for storing information about data collected from sensors.
    """

    __tablename__ = "sensor_records"
    # Latest-reading lookups (flow runner, per sensor) and per-sensor listings. Named explicitly
    # to match revision a1c2e3f4b5d6: the "ix" naming convention only sees Column objects, so the
    # text() expression would be dropped from an auto-generated name and `alembic check` would fail.
    __table_args__ = (
        Index("ix_sensor_records_sensor_serial_number_created_date", "sensor_serial_number", text("created_date DESC")),
    )

    sensor_serial_number = Column(
        String,
        ForeignKey("sensor.serial_number", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
        comment="Foreign key linking to a specific Sensor.",
    )
    data = Column(JSON, nullable=False, comment="JSON format containing the sensor data collected.")

    # Relationships

    # Many-to-One relationship with Sensor. Many SensorRecords will be created for a Sensor
    sensor = relationship(Sensor)
