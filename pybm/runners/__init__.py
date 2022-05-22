# flake8: noqa: F401
from .base import BaseRunner
from .gbm import GoogleBenchmarkRunner
from .timeit import TimeitRunner

runners = {
    "timeit": TimeitRunner,
    "gbm": GoogleBenchmarkRunner,
}
