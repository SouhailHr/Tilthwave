from infrastructure.database.tables.base import TilthwaveBaseModel
from sqlalchemy import Column, String, Date, Float, ForeignKey
from sqlalchemy.orm import relationship

from infrastructure.database.tables.zone import Zone


class Tree(TilthwaveBaseModel):
    """
    Tree model for storing tree information.
    """
    __tablename__ = 'tree'

    zone_name = Column(String, ForeignKey('zone.zone_name',  onupdate="CASCADE", ondelete="CASCADE"), nullable=False,
                       comment="Foreign key referencing the zone's name")
    variety = Column(String, nullable=False, comment="The species or variety of the tree")
    planting_date = Column(Date, nullable=False, comment="The date when the tree was planted")
    height = Column(Float, nullable=False, comment="Current height of the tree in meters")
    width_diameter = Column(Float, nullable=False, comment="Width or canopy diameter of the tree in meters")
    trunk_diameter = Column(Float, nullable=False, comment="Diameter of the tree trunk in centimeters")
    serial_number = Column(String(50), nullable=False, unique=True, comment='Unique serial number of the tree')

    # Relationships

    # Many-to-One relationship with Zone. A Zone can have multiple trees.
    zone = relationship(Zone)
