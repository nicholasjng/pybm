__version__ = "0.0.2"

# Disables flake8 errors for unused imports (project structuring)
# flake8: noqa: F401
from typing import Optional, List, Any, Dict

from pybm.config import PybmConfig, get_runner_class
from pybm.exceptions import PybmError
from pybm.runners.base import BenchmarkRunner
from pybm.status_codes import SUCCESS


def run(argv: Optional[List[str]] = None, context: Dict[str, Any] = None) -> int:
    """
    Syntactic sugar for dispatching a run inside a benchmark target file.
    The argv argument should realistically never need to be specified,
    while the context should almost always be the `globals()` object.
    """
    if context is None:
        raise PybmError(
            "Context is missing. When running a benchmark on a "
            "Python source file target, you need to pass the "
            "target's __main__ context in order for the "
            "benchmarks to be discovered correctly. You can do "
            'this e.g. by passing "globals()" as a value for '
            "the context object."
        )
    config_file = PybmConfig.load(".pybm/config.yaml")
    runner: BenchmarkRunner = get_runner_class(config_file)
    runner.run_benchmark(argv, context=context)
    return SUCCESS
