from pathlib import Path
from typing import Optional, Protocol

from pybm.config import config


class PybmIO(Protocol):
    def read(self, *args, **kwargs):
        ...

    def write(self, *args, **kwargs):
        ...


class BaseReporter:
    def __init__(self):
        self.result_dir: Path = Path(config.get_value("core.resultdir"))

        self.target_time_unit: str = config.get_value("reporter.timeunit")

        self.significant_digits: int = config.get_value("reporter.significantdigits")

        self.shalength: int = config.get_value("reporter.shalength")

        self.io: Optional[PybmIO] = None

    def compare(
        self,
        *refs: str,
        absolute: bool = False,
        previous: int = 1,
        target_filter: Optional[str] = None,
        benchmark_filter: Optional[str] = None,
        context_filter: Optional[str] = None
    ) -> None:
        raise NotImplementedError

    def read(self, *args, **kwargs):
        assert self.io is not None
        return self.io.read(*args, **kwargs)

    def write(self, *args, **kwargs):
        assert self.io is not None
        self.io.write(*args, **kwargs)
