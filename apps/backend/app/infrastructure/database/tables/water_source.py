from infrastructure.database.tables.base import TilthwaveBaseModel
from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship

# To avoid potential complications with import order and circular dependencies.
# such as mappers failing to initialize because they can't locate related classes during their configuration.
from infrastructure.database.tables.farm import Farm
from infrastructure.database.tables.sensor import Sensor


class WaterSource(TilthwaveBaseModel):
    """
    WaterSource model for storing WaterSource information.
    """
    __tablename__ = 'water_source'

    farm_name = Column(String, ForeignKey('farm.farm_name', onupdate="CASCADE", ondelete='SET NULL'), nullable=True,
                       comment='Foreign key referencing the farm')

    sensor_serial_number = Column(String, ForeignKey('sensor.serial_number', onupdate="CASCADE", ondelete='SET NULL'),
                                  nullable=True,unique=True,
                                  comment="Foreign key linking to a specific Sensor.")

    type = Column(String(50), nullable=False, comment='The type of water source')
    water_pressure = Column(Float, nullable=False, comment='Pressure of water at the source in PSI')
    water_volume = Column(Float, nullable=False, comment='Volume of water available at the source in cubic meters')
    status = Column(String(50), nullable=False,
                    comment='Operational status of the water source (e.g., "on", "off", "error")')
    serial_number = Column(String(50), nullable=False, unique=True, comment='Unique serial number of the water source')

    # Relationships
    # One-To-Many Relationship to the Farm model. Represents the farm that this water source belongs to it.
    farm = relationship(Farm)
    # One-To-one relationship with the Sensor model. Associates a sensor specifically with this water source.
    sensor = relationship(Sensor)

