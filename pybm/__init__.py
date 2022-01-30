__version__ = "0.0.3"

# Disables flake8 errors for unused imports (project structuring)
# flake8: noqa: F401
from typing import Optional, List, Any, Dict

from pybm.config import PybmConfig, get_component_class
from pybm.exceptions import PybmError
from pybm.runners import BaseRunner
from pybm.status_codes import SUCCESS


def run(argv: Optional[List[str]] = None, module_context: Dict[str, Any] = None) -> int:
    """
    Syntactic sugar for dispatching a run inside a benchmark target file.
    The argv argument should realistically never need to be specified,
    while the context should almost always be the `globals()` object.
    """
    if module_context is None:
        raise PybmError(
            "Missing module context. Please pass a module context for the benchmark "
            "(the easiest way to do this is by passing the globals() object)."
        )
    config_file = PybmConfig.load()

    runner: BaseRunner = get_component_class("runner", config_file)
    runner.run_benchmark(argv, module_context=module_context)

    return SUCCESS
