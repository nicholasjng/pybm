import typing
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from pybm.util.subprocess import run_subprocess


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


@dataclass(frozen=True)
class PythonSpec:
    """Dataclass representing a Python virtual environment."""

    executable: str = field()
    version: str = field()
    packages: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)

    def __post_init__(self):
        packages, locations = self.list()
        object.__setattr__(self, "packages", packages)
        object.__setattr__(self, "locations", locations)

    def list(self) -> Tuple[List[str], List[str]]:
        if self.executable == "":
            return [], []

        command = [self.executable, "-m", "pip", "list"]

        rc, pip_output = run_subprocess(command)

        # `pip list` output: table header, separator, package list
        flat_pkg_table = pip_output.splitlines()[2:]
        packages, locations = [], []

        for line in flat_pkg_table:
            split_line = line.split()
            packages.append("==".join(split_line[:2]))
            if len(split_line) > 2:
                locations.append(split_line[2])

        return packages, locations

    def update(self):
        packages, locations = self.list()
        self.packages.clear()
        self.packages.extend(packages)
        self.locations.clear()
        self.locations.extend(locations)
        return self


EmptyPythonSpec = PythonSpec(executable="", version="")
