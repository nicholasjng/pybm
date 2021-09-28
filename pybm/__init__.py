__version__ = "0.0.1"

# Disables flake8 errors for unused imports (project structuring)
# flake8: noqa: F401
from typing import Optional, List

from .config import PybmConfig, get_runner_class
from .runners.runner import BenchmarkRunner


def run(argv: Optional[List[str]] = None) -> int:
    config_file = PybmConfig.load(".pybm/config.yaml")
    runner: BenchmarkRunner = get_runner_class(config_file)
    return runner.run_benchmark(argv)
