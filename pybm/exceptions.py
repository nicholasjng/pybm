
class CommandError(Exception):
    def __init__(self, message):
        super(CommandError, self).__init__(message)
