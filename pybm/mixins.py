import operator
from typing import Optional, Any

from pybm.exceptions import PybmError


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
                raise PybmError(
                    f"Class {self.__class__.__name__!r} has no attribute {attr!r}."
                )
            else:
                return default

    def set_value(self, attr: str, value: str):
        *keys, subkey = attr.split(".")
        obj: Any = self

        for key in keys:
            obj = getattr(obj, key, None)

        if obj is None or not hasattr(obj, subkey):
            raise PybmError(
                f"Class {self.__class__.__name__!r} has no attribute {attr!r}."
            )

        value = self.canonicalize_type(obj, subkey, value)
        setattr(obj, subkey, value)

        return self

    @staticmethod
    def canonicalize_type(obj, attr: str, value: str):
        assert value is not None, "cannot set None config value"

        annotations = obj.__annotations__

        # if no annotation exists (this should not happen), interpret as string
        target_type = annotations.get(attr, str)

        try:
            if target_type != bool:
                # int, float, str
                return target_type(value)
            else:
                # bool(s) is True for all strings except the empty string,
                # so allow setting booleans with the true/false literal
                # like this
                if value.lower() == "false":
                    return False
                elif value.lower() == "true":
                    return True
                else:
                    # do not allow shorthands, y/n, 1/0 etc.
                    raise ValueError

        except ValueError:
            raise PybmError(
                f"Configuration value {attr!r} of class {obj.__class__.__name__} has "
                f"to be of type {target_type.__name__!r}, but the given value "
                f"{value!r} could not be interpreted as such."
            )
