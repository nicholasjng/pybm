import inspect
from typing import Callable, Tuple


def is_context_provider(func: Callable) -> bool:
    """Check whether a function is a valid benchmark context provider.
    A context provider is a function that takes no arguments and returns a
    2-tuple of context name and value."""
    func_sig = inspect.signature(func)
    takes_no_args = not bool(func_sig.parameters)
    has_correct_annotation = func_sig.return_annotation == Tuple[str, str]
    return takes_no_args and has_correct_annotation


def is_valid_timeit_target(func: Callable) -> bool:
    """Check whether a function is a valid target for timeit benchmarking
    with the standard library benchmark runner."""
    # TODO: Eventually, allow timeit methods taking arguments via some
    #  expression parsing
    func_sig = inspect.signature(func)
    takes_no_args = not bool(func_sig.parameters)
    return takes_no_args

