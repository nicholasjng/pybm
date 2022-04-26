import logging
import pathlib

from pybm.config import config


def get_logger(name: str):
    level: int = config.get_value("core.loglevel")
    fmt: str = config.get_value("core.logfmt")
    filename = pathlib.Path(config.get_value("core.logfile"))

    # ensure the logfile directory actually exists
    filename.parent.mkdir(parents=False, exist_ok=True)

    logging.basicConfig(filename=filename, format=fmt, level=level)

    logger = logging.getLogger(name=name)
    return logger
