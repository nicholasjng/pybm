import itertools
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, MutableMapping, Union

if TYPE_CHECKING:
    # Literal exists only from Python 3.8 onwards
    # solution source:
    # https://github.com/pypa/pip/blob/main/src/pip/_internal/utils/subprocess.py
    from typing import Literal

import yaml

from pybm.exceptions import PybmError
from pybm.mixins.state import NestedStateMixin
from pybm.specs import Package
from pybm.statuscodes import ERROR
from pybm.util.common import lmap
from pybm.util.git import get_main_worktree
from pybm.util.imports import import_from_module

__all__ = [
    "PybmConfig",
    "get_component",
    "get_runner_requirements",
    "config",
    "global_config",
    "LOCAL_CONFIG",
    "GLOBAL_CONFIG",
]

CONFIG_NAME = "config.yaml"
LOCAL_CONFIG = str(get_main_worktree() / Path(".pybm") / CONFIG_NAME)

if os.name == "nt":
    GLOBAL_CONFIG = str(Path(os.getenv("APPDATA", "")) / "pybm" / CONFIG_NAME)
else:
    GLOBAL_CONFIG = str(Path.home() / ".config" / "pybm" / CONFIG_NAME)


@dataclass
class CoreGroup:
    datefmt: str = "%d/%m/%Y %H:%M:%S"
    workspacefile: str = ".pybm/workspaces.yaml"
    logfile: str = "logs/logs.txt"
    logfmt: str = "%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"
    loglevel: int = logging.DEBUG
    resultdir: str = "results"


@dataclass
class GitGroup:
    basedir: str = ".."
    legacycheckout: bool = False


@dataclass
class RunnerGroup:
    name: str = "pybm.runners.TimeitRunner"
    failfast: bool = False
    contextproviders: str = ""


@dataclass
class ReporterGroup:
    name: str = "pybm.reporters.JSONConsoleReporter"
    timeunit: str = "usec"
    significantdigits: int = 2
    shalength: int = 8


@dataclass
class PybmConfig(NestedStateMixin):
    core: CoreGroup = CoreGroup()
    git: GitGroup = GitGroup()
    runner: RunnerGroup = RunnerGroup()
    reporter: ReporterGroup = ReporterGroup()

    def describe(self, attr):
        current = self.get_value(attr)
        if current is None:
            return ERROR

        group, name = attr.split(".")
        annotations: Dict[str, type] = self.get_value(group + ".__annotations__")
        value_type = annotations[name].__name__

        print(f"Describing configuration option {attr!r}.")
        print(f"Value type: {value_type}")
        print(f"Current value: {current!r}")
        print(description_db[group][name])

    @classmethod
    def from_dict(cls, config_obj: MutableMapping[str, Any], fill_value: Any = None):
        init_dict = {}

        for name, cfg_class in cls.__annotations__.items():
            config_keys = cfg_class.__annotations__.keys()
            cfg_dict = dict(zip(config_keys, [fill_value] * len(config_keys)))

            if name in config_obj:
                cfg_dict.update(config_obj[name])

            init_dict[name] = cfg_class(**cfg_dict)

        return cls(**init_dict)

    def items(self):
        return zip(self.keys(), self.values())

    def keys(self):
        def prepend_key(key: str, values: Iterable[str]):
            return map(lambda value: key + "." + value, values)

        return itertools.chain(
            *(prepend_key(k, asdict(v).keys()) for k, v in self.__dict__.items())
        )

    @classmethod
    def load(cls, path: Union[str, Path] = LOCAL_CONFIG):
        path = Path(path)

        if not path.exists():
            msg = f"Configuration file {str(path)!r} does not exist."

            if str(path) == LOCAL_CONFIG:
                msg += " Make sure to run `pybm init` to initialize pybm before use."
            raise PybmError(msg)

        with open(path, "r") as config_file:
            config_obj = yaml.load(config_file, Loader=yaml.FullLoader)

        return cls.from_dict(config_obj)

    def save(self, path: Union[str, Path] = LOCAL_CONFIG):
        with open(path, "w") as config_file:
            yaml.dump(self.to_dict(), config_file)

    def to_dict(self) -> MutableMapping[str, Any]:
        return {k: asdict(v) for k, v in self.__dict__.items()}

    def to_string(self):
        return yaml.dump(self.to_dict())

    def values(self):
        return itertools.chain(*(asdict(v).values() for v in self.__dict__.values()))


if Path(LOCAL_CONFIG).exists():
    config = PybmConfig.load()
else:
    config = PybmConfig()

if Path(GLOBAL_CONFIG).exists():
    global_config = PybmConfig.load(GLOBAL_CONFIG)
else:
    global_config = None


def get_component(kind: 'Literal["reporter", "runner"]'):
    cls = import_from_module(config.get_value(f"{kind}.name"))
    return cls()


def get_runner_requirements() -> List[str]:
    pkgs: List[Package] = get_component("runner").required_packages
    return lmap(str, pkgs)


description_db: Dict[str, Dict[str, str]] = {
    "core": {
        "datefmt": "Datetime format string used to format timestamps for workspace "
        "creation and modification. For a comprehensive list of identifiers and "
        "options, check the standard library documentation on datetime.strftime: "
        "https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior.",
        "loglevel": "Default level to be used in pybm logging.",
        "logfile": "Name of the log file to write debug logs to.",
        "logfmt": "Formatter string used to format logs in pybm. "
        "For a comprehensive list of identifiers and options, check the "
        "Python standard library documentation on logging formatters: "
        "https://docs.python.org/3/library/logging.html#formatter-objects.",
    },
    "git": {
        "basedir": "Where to create new git worktrees. This value is set with the "
        "parent directory of your repository as default. Some IDEs may get confused "
        "when you initialize another git worktree inside your main repository, so "
        "this option provides an easy way to maintain a clean repository.",
        "legacycheckout": "Whether to use the `git checkout <ref> -- <source>` "
        "command to source benchmark files from another ref instead of `git "
        "restore --source <ref> <source>`. The latter command is better suited for "
        "this purpose, but requires at minimum git version 2.23. Setting this option "
        "to 'true' allows the use of older git versions for this purpose.",
    },
    "runner": {
        "name": "Name of the runner class used in pybm to run benchmarks inside Python "
        "virtual environments. If you want to supply your own custom runner class, set "
        "this value to your custom subclass of pybm.runners.BaseRunner.",
        "failfast": "Whether to abort the benchmark process prematurely on the first "
        "encountered exception instead of continuing until completion.",
        "contextproviders": "A colon-separated list of context provider functions. "
        "In pybm benchmarks, context can be given to include additional information in "
        "the resulting JSON files. A context provider in pybm takes no arguments and "
        "returns two strings used as key and value for the benchmark context object.",
    },
    "reporter": {
        "name": "Name of the reporter class used in pybm to report and compare "
        "benchmark results. If you want to supply your own custom reporter class, "
        "set this value to your custom subclass of pybm.reporters.BaseReporter.",
        "timeunit": "Time unit for benchmark timings. Valid options are s/sec, "
        "ms/msec, us/usec, and ns/nsec, where either spelling is admissible.",
        "significantdigits": "Number of significant digits to round floating point "
        "results to in console display.",
        "shalength": "Length of git SHA fragments to display in console output. "
        "Default value is 8, meaning the first eight hex digits are displayed.",
    },
}
