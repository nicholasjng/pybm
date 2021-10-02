import inspect
from typing import Callable, Tuple, Any


def is_context_provider(func: Callable) -> bool:
    """Check whether a function is a valid benchmark context provider.
    A context provider is a function that takes no arguments and returns a
    2-tuple of context name and value."""
    func_sig = inspect.signature(func)
    takes_no_args = not bool(func_sig.parameters)
    has_correct_annotation = func_sig.return_annotation == Tuple[str, str]
    return takes_no_args and has_correct_annotation


def is_valid_timeit_target(func_obj: Tuple[str, Any]) -> bool:
    """Check whether a function is a valid target for timeit benchmarking
    with the standard library benchmark runner."""
    name, func = func_obj
    is_func = inspect.isfunction(func)
    if not is_func:
        return False
    func_sig = inspect.signature(func)
    takes_no_args = not bool(func_sig.parameters)
    return takes_no_args
