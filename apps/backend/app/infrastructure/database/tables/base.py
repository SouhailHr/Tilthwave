from sqlalchemy import Column, DateTime, Integer, String

from common.dates import utc_now
from infrastructure.database.base_class import Base


class TilthwaveBaseModel(Base):
    """
    Base model containing common fields for all the Tilthwave tables.
    Timestamps are naive UTC (common.dates.utc_now), the same clock the use cases compare against.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Unique identifier for the record.")
    # NOT NULL with a UTC server default in Postgres (revision c3d4e5f6a7b8), so rows written outside
    # the ORM are stamped too and can never sort first under `ORDER BY created_date DESC`.
    created_date = Column(
        DateTime, default=utc_now, nullable=False, comment="Date and time when the record was created."
    )
    updated_date = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        comment="Date and time when the record was last updated.",
    )
    performed_by = Column(
        String, default=None, nullable=True, comment="A field states who is the user that did the action"
    )
