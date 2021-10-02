import functools
import re
from pathlib import Path
from typing import List, Any, Dict, Union, Optional, Tuple

from pybm.exceptions import PybmError
from pybm.specs import BenchmarkEnvironment
from pybm.util.common import lfilter, dfilter, dkfilter
from pybm.util.functions import is_context_provider
from pybm.util.imports import import_from_module
from pybm.util.path import get_subdirs


def create_rundir(result_dir: Union[str, Path]) -> Path:
    # int key prevents unexpected sorting results for more then 10
    # directories (order 1 -> 10 -> 2 -> 3 ...)
    subdirs = sorted(get_subdirs(result_dir), key=int)
    folder = str(len(subdirs) + 1)
    result_path = Path(result_dir) / folder
    # result subdirectory should not exist at this point.
    result_path.mkdir(parents=False, exist_ok=False)
    return result_path


def create_subdir(result_dir: Union[str, Path],
                  environment: BenchmarkEnvironment) -> Path:
    ref, ref_type = environment.worktree.get_ref_and_type()
    if ref_type in ["branch", "tag"]:
        suffix = ref.split("/", maxsplit=2)[-1]
        suffix = suffix.replace("/", "-")
    else:
        suffix = ref
    result_subdir = Path(result_dir) / suffix
    result_subdir.mkdir(parents=False, exist_ok=False)
    return result_subdir


def filter_targets(module_context: Dict[str, Any],
                   regex_filter: Optional[str] = None):
    # filter admissible targets as those from the __main__ module
    # of the subprocess (target .py file)
    is_main_member = functools.partial(is_module_member,
                                       module_name="__main__")
    filtered_context = dfilter(is_main_member, module_context)
    if regex_filter is not None:
        pattern = re.compile(regex_filter)
        filtered_context = dkfilter(
            lambda k: pattern.search(k) is not None, filtered_context)
    return filtered_context


def is_module_member(obj_tuple: Tuple[str, Any], module_name: str):
    """Check membership of object in __main__ module to avoid benchmarking
    imports due to accidentally pattern matching them."""
    obj = obj_tuple[1]
    if not hasattr(obj, "__module__"):
        return False
    else:
        return obj.__module__ == module_name



def load_context_providers(provider_info: str) -> List[Any]:
    if provider_info != "":
        provider_names = provider_info.split(",")
    else:
        return []
    # require the context providers to come from an installed module
    imported = [import_from_module(name) for name in provider_names]
    return lfilter(is_context_provider, imported)


def validate_context(context: List[str], parsed: bool = False):
    """Validate a set of context information, either parsed (=with flag
    name and prefix chars stripped) or unparsed (the raw flags)."""
    expected_length: int = 2 if parsed else 3
    for ctx_val in context:
        seen: Dict[str, str] = {}
        split_ctx = ctx_val.split("=")
        if len(split_ctx) != expected_length:
            raise PybmError("Could not properly parse context value "
                            f"{ctx_val!r}. Context values need to be "
                            f"given as arguments in the format "
                            f"\"--context=<key>=<value>\".")
        name, value = split_ctx[-2:]
        if name in seen:
            raise PybmError(f"Multiple values for context value "
                            f"{name!r} were supplied. Perhaps you "
                            f"gave some context information twice, "
                            f"once on the command line as global context, "
                            f"and via a set environment-specific context "
                            f"provider. To check the currently set "
                            f"environment-specific context providers, "
                            f"run the command "
                            f"`pybm config get runner.contextProviders`.")
