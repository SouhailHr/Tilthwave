from common.exceptions import TilthwaveBaseException


class UseCaseException(TilthwaveBaseException):
    def __init__(self, class_name=None, message=None, *args):
        super().__init__(message, *args)

        self.class_name = class_name

    def __str__(self):
        msg = super().__str__()
        return f"{self.class_name}: {msg}"
