__version__ = "0.1.0"

# Disables flake8 errors for unused imports (project structuring)
# flake8: noqa: F401
import sys
from typing import Any, Dict, List, Optional

from pybm.config import get_component
from pybm.exceptions import PybmError
from pybm.runners import BaseRunner, runners
from pybm.statuscodes import SUCCESS


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

    argv = argv or sys.argv
    *argv, name_flag = argv

    # runner name given as kwarg --runner=<name>
    name = name_flag.split("=")[-1]

    if name in runners:
        runner: BaseRunner = runners[name]()
    else:
        runner = get_component("runner")

    runner.run_benchmark(argv, module_context=module_context)

    return SUCCESS
