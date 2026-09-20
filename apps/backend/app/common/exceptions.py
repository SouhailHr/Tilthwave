class TilthwaveBaseException(Exception):
    """
    Root of the domain exception hierarchy.

    Layers raise a subclass instead of a bare Exception so the API layer can
    translate them to one HTTP status each (see interfaces/api/helpers/errors.py)
    without inspecting messages.
    """

    def __init__(self, message=None, *args):
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"


class NotFoundError(TilthwaveBaseException):
    """The object does not exist, or lies outside the caller's farm (we do not reveal which)."""


class ConflictError(TilthwaveBaseException):
    """A uniqueness or foreign-key constraint was violated."""


class InvalidFilterError(TilthwaveBaseException):
    """A Filter DSL entry references an unknown attribute or an unsupported condition."""


class BrokerError(TilthwaveBaseException):
    """Publishing a command to the broker failed; the physical state may not have changed."""
