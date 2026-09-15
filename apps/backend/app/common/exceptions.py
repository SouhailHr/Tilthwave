class TilthwaveBaseException(Exception):
    def __init__(self, message=None, *args):
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        return f"{self.__class__.__name__ }: {self.message}"
