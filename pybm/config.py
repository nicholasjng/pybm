import itertools
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Union, Dict, List, Any, MutableMapping, TYPE_CHECKING, Iterable

from pybm.status_codes import ERROR
from pybm.util.common import lmap
from pybm.util.git import get_main_worktree

if TYPE_CHECKING:
    # Literal exists only from Python 3.8 onwards
    # solution source:
    # https://github.com/pypa/pip/blob/main/src/pip/_internal/utils/subprocess.py
    from typing import Literal

import toml

from pybm.exceptions import PybmError
from pybm.mixins import StateMixin
from pybm.specs import (
    CoreGroup,
    BuilderGroup,
    RunnerGroup,
    GitGroup,
    ReporterGroup,
    Package,
)
from pybm.util.imports import import_from_module

__all__ = [
    "PybmConfig",
    "get_component_class",
    "get_runner_requirements",
    "LOCAL_CONFIG",
    "GLOBAL_CONFIG",
]

CONFIG_NAME = "config.toml"
LOCAL_CONFIG = str(get_main_worktree() / Path(".pybm") / CONFIG_NAME)

if os.name == "nt":
    GLOBAL_CONFIG = str(Path(os.getenv("APPDATA", "")) / "pybm" / CONFIG_NAME)
else:
    GLOBAL_CONFIG = str(Path(os.getenv("HOME", "")) / ".config" / "pybm" / CONFIG_NAME)


@dataclass
class PybmConfig(StateMixin):
    core: CoreGroup = CoreGroup()
    git: GitGroup = GitGroup()
    builder: BuilderGroup = BuilderGroup()
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
                msg += "Make sure to run `pybm init` to initialize pybm before use."
            raise PybmError(msg)

        with open(path, "r") as config_file:
            config_obj = toml.load(config_file)

        return cls.from_dict(config_obj)

    def save(self, path: Union[str, Path] = LOCAL_CONFIG):
        with open(path, "w") as config_file:
            toml.dump(self.to_dict(), config_file)

    def to_dict(self) -> MutableMapping[str, Any]:
        return {k: asdict(v) for k, v in self.__dict__.items()}

    def to_string(self):
        return toml.dumps(self.to_dict())

    def values(self):
        return itertools.chain(*(asdict(v).values() for v in self.__dict__.values()))


def get_component_class(
    kind: 'Literal["builder", "reporter", "runner"]', config: PybmConfig
):
    cls = import_from_module(config.get_value(f"{kind}.name"))
    return cls(config)


def get_runner_requirements(config: PybmConfig) -> List[str]:
    pkgs: List[Package] = get_component_class("runner", config).required_packages
    return lmap(str, pkgs)


description_db: Dict[str, Dict[str, str]] = {
    "core": {
        "datefmt": "Datetime format string used to format timestamps for environment "
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
    "builder": {
        "name": "Name of the builder class used in pybm to manage "
        "virtual Python environments. If you want to supply your own custom builder "
        "class, set this value to your custom subclass of pybm.builders.BaseBuilder.",
        "homedir": "Optional home directory containing pre-built virtual environments. "
        "The default for pybm is to create the virtual environment directly into the "
        "new git worktree, but you can also choose to link existing environments, "
        "which are assumed to be subdirectories of this location.",
        "autoinstall": "Whether to install the configured benchmark runner's "
        "dependencies immediately into a newly created virtual environment. Unset this "
        "option for more granular control over the installation process.",
        "wheelcaches": "A string of local directories separated by colons (':'), like "
        "a Unix PATH variable, containing prebuilt wheels for Python packages. "
        "Set this if you request a package that has no wheels for your Python version "
        "or architecture available, and you have to build wheels yourself.",
        "pipinstalloptions": "Comma-separated list of options passed to `pip install` "
        "in builders using pip. Set this if you use a number of `pip install` options "
        "consistently, and do not want to type them out in every `pybm env install`.",
        "pipuninstalloptions": "Comma-separated list of options passed to `pip "
        "uninstall` in builders using pip. Set this if you use a number of `pip "
        "uninstall` options consistently, and do not want to type them out in every "
        "`pybm env uninstall`.",
        "venvoptions": "Comma-separated list of options for virtual environment "
        "creation in a venv-based builder. Set this if you use a number of `python -m "
        "venv` options consistently, and do not want to type them out in every "
        "`pybm env create` call.",
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
    },
}
