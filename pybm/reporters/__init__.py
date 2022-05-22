# flake8: noqa: F401
from .base import BaseReporter
from .console import JSONConsoleReporter

reporters = {
    "console": JSONConsoleReporter,
}
