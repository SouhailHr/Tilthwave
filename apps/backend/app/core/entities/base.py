import dataclasses
from typing import ClassVar


@dataclasses.dataclass
class BaseEntity:
    """
    BaseEntity is an Abstract Class
    """

    # Fields that must never leave the service through the API (secrets, hashes).
    # Declared per entity so a new secret field is hidden by adding one name here,
    # not by remembering to override a method.
    PRIVATE_FIELDS: ClassVar[tuple] = ()

    @classmethod
    def from_dict(cls, data: dict):
        """
        Create an instance of cls from a given dictionary.
        @param data: Dictionary with keys matching class attributes.
        @return: Instance of cls.
        """
        return cls(**data)

    def to_dict(self):
        """
        Convert the instance to dictionary, complete. Repositories persist from it.
        @return: Dictionary representation of the instance.
        """
        return dataclasses.asdict(self)

    def to_public_dict(self):
        """
        Dictionary representation safe to return from the API: to_dict() minus PRIVATE_FIELDS.
        @return: Dictionary representation of the instance.
        """
        data = self.to_dict()
        for field in self.PRIVATE_FIELDS:
            data.pop(field, None)
        return data
