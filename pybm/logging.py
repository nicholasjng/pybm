import logging
import pathlib
import sys

# import pybm

FORMAT = "%(asctime)s — %(name)-12s — %(levelname)s — %(message)s"
DATEFORMAT = '%d/%m/%Y %I:%M:%S %p'
FORMATTER = logging.Formatter(fmt=FORMAT, datefmt=DATEFORMAT)
LOGFILE = "logs/logs.txt"
DEFAULT_LEVEL = logging.WARNING


def get_file_handler():
    # pybm.PybmConfig.load(".pybm/config.yaml")
    pathlib.Path(LOGFILE).parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(filename=LOGFILE, mode="a+")
    file_handler.setLevel(DEFAULT_LEVEL)
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_stream_handler():
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(FORMATTER)
    stream_handler.setLevel(DEFAULT_LEVEL)
    return stream_handler


def get_logger(name: str):
    logger = logging.getLogger(name=name)
    logger.setLevel(DEFAULT_LEVEL)
    logger.addHandler(get_file_handler())
    return logger
