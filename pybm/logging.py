import logging
import pathlib
import sys

from pybm import PybmConfig, PybmError


def get_file_handler(config: PybmConfig):
    logfile = pathlib.Path(config.get_value("core.logfile"))
    logfile.parent.mkdir(parents=False, exist_ok=True)
    file_handler = logging.FileHandler(filename=logfile, mode="a+")
    file_handler.setLevel(config.get_value("core.loglevel"))
    file_handler.setFormatter(config.get_value("core.logfmt"))
    return file_handler


def get_stream_handler(config: PybmConfig):
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(config.get_value("core.logfmt"))
    stream_handler.setLevel(config.get_value("core.loglevel"))
    return stream_handler


def get_logger(name: str):
    logger = logging.getLogger(name=name)
    try:
        config = PybmConfig.load()
    except PybmError:
        # run with default settings
        config = PybmConfig()

    logger.setLevel(config.get_value("core.loglevel"))
    logger.addHandler(get_file_handler(config=config))
    return logger
