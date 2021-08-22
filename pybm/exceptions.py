import os
import sys


class CommandError(ValueError):
    pass


class ArgumentError(ValueError):
    pass


class GitError(ValueError):
    pass


class VenvError(ValueError):
    pass


def write_exception_info(info: Exception, origin: str = None):
    if origin:
        info_str = f"Error using {origin}: {info}"
    else:
        info_str = f"Error: {info}"
    sys.stderr.write(info_str)
    sys.stderr.write(os.linesep)
