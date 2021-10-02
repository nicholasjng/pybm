__version__ = "0.0.1"

# Disables flake8 errors for unused imports (project structuring)
# flake8: noqa: F401
from typing import Optional, List, Any, Dict

from .config import PybmConfig, get_runner_class
from .runners.runner import BenchmarkRunner
from .status_codes import SUCCESS


def run(argv: Optional[List[str]] = None,
        context: Dict[str, Any] = None) -> int:
    """
    Syntactic sugar for dispatching a run inside a benchmark target file.
    The argv argument should realistically never need to be specified,
    while the context should almost always be the `globals()` object.
    """
    config_file = PybmConfig.load(".pybm/config.yaml")
    runner: BenchmarkRunner = get_runner_class(config_file)
    runner.run_benchmark(argv, context=context)
    return SUCCESS
