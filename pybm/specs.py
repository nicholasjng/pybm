import typing
from typing import Optional


class Package(typing.NamedTuple):
    name: str
    version: Optional[str] = None
    origin: Optional[str] = None

    def __str__(self):
        if self.version is not None and self.origin is None:
            return self.name + "==" + self.version
        elif self.version is not None and self.origin is not None:
            return self.origin + "@" + self.version
        elif self.version is None and self.origin is not None:
            return self.origin
        else:
            return self.name
