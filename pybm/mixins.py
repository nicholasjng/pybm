import operator
import subprocess
from typing import Optional, Any, List, Tuple

from pybm.exceptions import PybmError
from pybm.logging import get_logger

logger = get_logger(__name__)


# TODO: Rethink this
class SubprocessMixin:
    """Useful utilities for CLI command wrappers such as for git, venv."""

    def __init__(self, exception_type: type):
        self.exception_type = exception_type

    def run_subprocess(self,
                       command: List[str],
                       reraise_on_error: bool = True,
                       print_status: bool = True,
                       **subprocess_kwargs) -> Tuple[int, str]:
        # TODO: Move printing in here entirely to avoid fragmentation
        full_command = " ".join(command)
        logger.debug(f"Running command {full_command}...")
        p = subprocess.run(command,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           encoding="utf-8",
                           **subprocess_kwargs)
        rc = p.returncode
        if rc != 0:
            msg = f"The command `{full_command}` returned the non-zero " \
                  f"exit code {rc}.\nFurther information (stderr " \
                  f"output of the subprocess):\n{p.stderr}"
            if print_status:
                print("failed.")
                if not reraise_on_error:
                    print(msg)
            if reraise_on_error:
                raise self.exception_type(msg)
        return rc, p.stdout


class StateMixin:
    """
    State getter and setter methods based on dotted attribute access.

    Usage works as follows: X.get_value("a.b") returns the nested attribute
    b on object a, which itself is a member of class X. Same for set_value.
    """

    def get_value(self, attr: str, default: Optional[Any] = None) -> Any:
        lookup = operator.attrgetter(attr)
        try:
            return lookup(self)
        except AttributeError:
            if default is None:
                raise PybmError(f"Class {self.__class__.__name__!r} has no "
                                f"attribute {attr!r}.")
            else:
                return default

    def set_value(self, attr: str, value: Any):
        *subkeys, key = attr.split(".")
        obj = self
        for subkey in subkeys:
            obj = getattr(obj, subkey, None)
        if obj is None or not hasattr(obj, key):
            # print("failed.")
            raise PybmError(f"Class {self.__class__.__name__!r} has no "
                            f"attribute {attr!r}.")
        canonicalized_value = self.canonicalize_type(obj, key, value)
        setattr(obj, key, canonicalized_value)
        return self

    @staticmethod
    def canonicalize_type(obj, attr: str, value: str):
        annotations = obj.__annotations__
        # if no annotation exist (this should not happen), interpret as string
        target_type = annotations.get(attr, str)
        if isinstance(value, target_type):
            # TODO: Maybe scrutinize string inputs for if they make sense?
            return value
        else:
            try:
                return target_type(value)
            except ValueError:
                print("failed.")
                raise PybmError(f"Configuration value \"{attr}\" of class "
                                f"{obj.__class__.__name__} has to be of type "
                                f"\"{target_type.__name__}\", but the given "
                                f"value {value} could not be "
                                f"interpreted as such.")
