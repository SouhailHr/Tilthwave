from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from infrastructure.database.tables.base import TilthwaveBaseModel
from infrastructure.database.tables.zone import Zone


class IrrigationTask(TilthwaveBaseModel):
    """
    IrrigationTask model for storing IrrigationTask information.
    """

    __tablename__ = "irrigation_task"
    # The flow runner asks for a zone's in-progress task every tick and the dashboard counts by
    # status; both filter on these two columns (revision d4e5f6a7b8c9).
    __table_args__ = (Index("ix_irrigation_task_zone_name_status", "zone_name", "status"),)

    zone_name = Column(
        String,
        ForeignKey("zone.zone_name", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
        comment="Foreign key linking to the Zone where the task is applied",
    )
    status = Column(
        String, nullable=False, comment="Current status of the task (e.g., pending, in progress, completed, canceled)"
    )
    duration = Column(Integer, nullable=True, comment="Duration of the irrigation process in minutes")
    # Relationships

    # Many-to-One relationship with Zone. The Zone can have Multiple Irrigation Tasks
    zone = relationship(Zone)
