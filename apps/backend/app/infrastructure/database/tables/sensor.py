from sqlalchemy import Column, String, Boolean

from infrastructure.database.tables.base import TilthwaveBaseModel


class Sensor(TilthwaveBaseModel):
    """
    Sensor model for storing Sensor information.
    """
    __tablename__ = 'sensor'

    type = Column(String(100), nullable=False,
                  comment='Type of the sensor (e.g., switcher_sensor, water_source_sensor, temperature_sensor, '
                          'moisture_sensor, saturation_sensor)')
    is_active = Column(Boolean, default=True, nullable=False,
                       comment='General status of the sensor (e.g., active, inactive)')

    serial_number = Column(String(50), nullable=False, unique=True, comment='Unique serial number of the sensor')

    # Relationships
