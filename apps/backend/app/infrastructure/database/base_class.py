from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import as_declarative

# Deterministic constraint names: Alembic autogenerate then never emits `None` names, which made
# the head revision impossible to downgrade (drop_constraint(None, ...)). Matches Postgres' own
# defaults for FK/unique/pk so existing tables need no rename.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}


@as_declarative(metadata=MetaData(naming_convention=NAMING_CONVENTION))
class Base:
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
