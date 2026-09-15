import datetime
from sqlalchemy import Column, DateTime, Integer, String
from infrastructure.database.base_class import Base


class TilthwaveBaseModel(Base):
    """
    Base model containing common fields for all the Tilthwave tables.
    """
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Unique identifier for the record.")
    created_date = Column(DateTime, default=datetime.datetime.utcnow,
                          comment="Date and time when the record was created.")
    updated_date = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow,
                          comment="Date and time when the record was last updated.")
    performed_by = Column(String, default=None, nullable=True,
                          comment="A field states who is the user that did the action")
