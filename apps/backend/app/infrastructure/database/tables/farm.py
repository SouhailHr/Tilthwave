from sqlalchemy import Column, String, Float, JSON

from infrastructure.database.tables.base import TilthwaveBaseModel


# To avoid potential complications with import order and circular dependencies.
# such as mappers failing to initialize because they can't locate related classes during their configuration.


class Farm(TilthwaveBaseModel):
    __tablename__ = 'farm'

    farm_name = Column(String(100), unique=True, nullable=False, comment='The unique name of the farm.')
    address = Column(String(255), nullable=False, comment='The physical address of the farm.')
    location = Column(JSON, nullable=True, comment='A JSON object storing detailed location data such as coordinates.')
    size = Column(Float, nullable=False, comment='The total area of the farm in acres.')


