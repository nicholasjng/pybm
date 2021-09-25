import importlib
import importlib.util
import sys
from pathlib import Path
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import Callable, Union

from pybm.exceptions import PybmError


def module_exists(module_name: str):
    spec = importlib.util.find_spec(module_name)
    return spec is not None


def import_module_from_source(source_path: Union[str, Path]) -> ModuleType:
    # TODO: Use path and extension to come up with a unique name here
    p = Path(source_path)
    if not p.exists():
        raise PybmError(f"Source path {source_path} does not exist.")
    elif p.suffix != ".py":
        raise PybmError(f"Source path {source_path} is not a Python file.")

    # strip away .py extension and cast to module syntax
    py_name = p.with_suffix("").as_posix().replace("/", ".")
    if py_name in sys.modules:
        # return loaded module
        return sys.modules[py_name]
    spec: ModuleSpec = importlib.util.spec_from_file_location(py_name,
                                                              source_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def import_func_from_source(source_path: str, fn_name: str) -> Callable:
    """Imports a function from a module provided as source file."""

    try:
        # Source:
        # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
        module = import_module_from_source(source_path)
        return getattr(module, fn_name)
    except (AttributeError, PybmError) as e:
        raise PybmError(f"Failed to import function {fn_name} from source "
                        f"file {source_path}.") from e


def import_from_module(identifier: str) -> Callable:
    """Imports a function or class from a path given in Python module syntax,
    e.g. my.module.my_function ."""
    *module_parts, name = identifier.split(".")
    module_name = ".".join(module_parts)
    if not module_exists(module_name):
        raise PybmError(f"Module {module_name} does not exist in the current "
                        f"Python environment.")
    module = importlib.import_module(module_name)
    return getattr(module, name)


def import_function(name: str):
    func = None
    try:
        func = import_from_module(name)
    except (PybmError, AttributeError):
        pass
    try:
        source_path, fn_name = name.split(":")
        func = import_func_from_source(source_path=source_path,
                                       fn_name=fn_name)
    except (PybmError, AttributeError):
        pass
    return func
