import dataclasses


@dataclasses.dataclass
class BaseEntity:
    """
    BaseEntity is an Abstract Class
    """

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
        Convert the instance to dictionary.
        @return: Dictionary representation of the instance.
        """
        return dataclasses.asdict(self)
