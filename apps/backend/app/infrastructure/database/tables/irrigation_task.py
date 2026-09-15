from sqlalchemy import Column, String, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship

from infrastructure.database.tables.base import TilthwaveBaseModel
from infrastructure.database.tables.zone import Zone


class IrrigationTask(TilthwaveBaseModel):
    """
    IrrigationTask model for storing IrrigationTask information.
    """
    __tablename__ = 'irrigation_task'

    zone_name = Column(String, ForeignKey('zone.zone_name', onupdate="CASCADE", ondelete='SET NULL'), nullable=True,
                       comment="Foreign key linking to the Zone where the task is applied")
    status = Column(String, nullable=False,
                    comment="Current status of the task (e.g., pending, in progress, completed, canceled)")
    duration = Column(Integer, nullable=True, comment="Duration of the irrigation process in minutes")
    # Relationships

    # Many-to-One relationship with Zone. The Zone can have Multiple Irrigation Tasks
    zone = relationship(Zone)
