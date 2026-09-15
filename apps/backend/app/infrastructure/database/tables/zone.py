from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship

from infrastructure.database.tables.base import TilthwaveBaseModel
from infrastructure.database.tables.farm import Farm


# To avoid potential complications with import order and circular dependencies.
# such as mappers failing to initialize because they can't locate related classes during their configuration.


class Zone(TilthwaveBaseModel):
    """
    Zone model for storing zone information.
    """
    __tablename__ = 'zone'

    farm_name = Column(String, ForeignKey('farm.farm_name', onupdate="CASCADE", ondelete='SET NULL'), nullable=True,
                       comment='Foreign key referencing the farm')
    zone_name = Column(String, unique=True, nullable=False, comment='Unique name of the zone.')
    size = Column(Integer, comment='Size of the zone in square meters.')
    location = Column(JSON, nullable=True, comment='Geographical details of the zone stored in JSON format.')
    soil_type = Column(String, comment='Type of soil within the zone.')

    # Triggers for the zone irrigation
    moisture_trigger_start = Column(Integer, comment='Moisture trigger start value.')
    moisture_trigger_stop = Column(Integer, comment='Moisture trigger stop value.')
    saturation_trigger_start = Column(Integer, comment='Saturation trigger start value.')
    saturation_trigger_stop = Column(Integer, comment='Saturation trigger stop value.')

    # Relationships

    # Many-to-One relationship with Farm. A farm can have multiple zones.
    farm = relationship(Farm)

