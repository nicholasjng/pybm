from pybm import PybmConfig
from pathlib import Path
from typing import Union, Optional


class BenchmarkReporter:
    def __init__(self, config: PybmConfig):
        self.result_dir: Path = Path(config.get_value(
            "reporter.resultDirectory"))
        self.target_time_unit: str = config.get_value(
            "reporter.targetTimeUnit")
        self.significant_digits: int = config.get_value(
            "reporter.significantDigits"
        )

    def add_arguments(self):
        raise NotImplementedError

    def compare(self,
                *refs: str,
                result: Union[str, Path],
                target_filter: Optional[str] = None,
                benchmark_filter: Optional[str] = None,
                context_filter: Optional[str] = None
                ):
        raise NotImplementedError

    def report(self,
               ref: str,
               result: Union[str, Path],
               target_filter: Optional[str] = None,
               benchmark_filter: Optional[str] = None,
               context_filter: Optional[str] = None):
        raise NotImplementedError

    def load(self, ref: str, result: Union[str, Path],
             target_filter: Optional[str] = None):
        raise NotImplementedError
