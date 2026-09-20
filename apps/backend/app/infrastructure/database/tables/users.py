from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from infrastructure.database.tables.base import TilthwaveBaseModel
from infrastructure.database.tables.farm import Farm


class Users(TilthwaveBaseModel):
    """
    User model for storing user information including personal details and role.
    """

    __tablename__ = "users"

    username = Column(String(50), unique=True, nullable=False, comment="Username of the user.")
    email = Column(String(100), unique=True, nullable=False, comment="Email address of the user.")
    phone_number = Column(String(30), nullable=False, comment="Contact phone number of the user.")
    password = Column(String(80), nullable=False, comment="Hashed password of the user.")
    first_name = Column(String(50), nullable=False, comment="First name of the user.")
    last_name = Column(String(50), nullable=False, comment="Last name of the user.")
    role = Column(String(10), nullable=False, comment="Role of the user within the system.")
    is_active = Column(
        Boolean, default=True, nullable=False, comment="Status indicating whether the user account is active."
    )
    is_superuser = Column(
        Boolean, default=False, comment="Status indicating whether the user account is Superuser ( admin or owner )."
    )

    farm_name = Column(
        String(100),
        ForeignKey("farm.farm_name", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
        comment="The name of the farm managed by the user.",
    )

    # Relationships

    farm = relationship(Farm)
