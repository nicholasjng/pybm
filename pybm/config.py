from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Union, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    # Literal exists only from Python 3.8 onwards
    # solution source:
    # https://github.com/pypa/pip/blob/main/src/pip/_internal/utils/subprocess.py
    from typing import Literal

import toml

from pybm.exceptions import PybmError
from pybm.mixins import StateMixin
from pybm.specs import CoreGroup, BuilderGroup, RunnerGroup, GitGroup, ReporterGroup
from pybm.util.imports import import_from_module

__all__ = [
    "PybmConfig",
    "get_component_class",
    "get_runner_requirements",
]

Descriptions = Dict[str, str]

CONFIG = ".pybm/config.toml"


@dataclass
class PybmConfig(StateMixin):
    core: CoreGroup = CoreGroup()
    git: GitGroup = GitGroup()
    builder: BuilderGroup = BuilderGroup()
    runner: RunnerGroup = RunnerGroup()
    reporter: ReporterGroup = ReporterGroup()

    def describe(self, attr):
        current = self.get_value(attr)
        group, name = attr.split(".")
        annotations: Dict[str, type] = self.get_value(group + ".__annotations__")
        value_type = annotations[name].__name__

        print(f"Describing configuration option {attr!r}.")
        print(f"Value type: {value_type}")
        print(f"Current value: {current!r}")
        print(
            description_db[group].get(
                name, f"No description available for {group} option {name!r}."
            )
        )

    @classmethod
    def load(cls, path: Union[str, Path] = CONFIG):
        if isinstance(path, str):
            path = Path(path)

        if not path.exists() or not path.is_file():
            raise PybmError(
                f"Configuration file {path} does not exist. "
                f"Make sure to run `pybm init` before using pybm "
                f"to set up environments or run benchmarks."
            )

        with open(path, "r") as config_file:
            cfg = toml.load(config_file)

        return PybmConfig(
            core=CoreGroup(**cfg["core"]),
            git=GitGroup(**cfg["git"]),
            runner=RunnerGroup(**cfg["runner"]),
            builder=BuilderGroup(**cfg["builder"]),
            reporter=ReporterGroup(**cfg["reporter"]),
        )

    def save(self, path: Union[str, Path] = CONFIG):
        with open(path, "w") as config_file:
            toml.dump(self.to_dict(), config_file)

    def to_dict(self):
        return {
            "core": asdict(self.core),
            "git": asdict(self.git),
            "runner": asdict(self.runner),
            "builder": asdict(self.builder),
            "reporter": asdict(self.reporter),
        }

    def to_string(self):
        return toml.dumps(self.to_dict())


def get_component_class(
    kind: 'Literal["builder", "reporter", "runner"]', config: PybmConfig
):
    class_name = import_from_module(config.get_value(f"{kind}.name"))
    return class_name(config)


def get_runner_requirements(config: PybmConfig) -> List[str]:
    return get_component_class("runner", config).required_packages


description_db: Dict[str, Descriptions] = {
    "core": {
        "datefmt": "Datetime format string used to format timestamps for environment "
        "creation and modification. For a comprehensive list of identifiers and "
        "options, check the standard library documentation on datetime.strftime: "
        "https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior.",
        "loglevel": "Default level to be used in pybm logging.",
        "logfile": "Name of the log file to write debug logs to, like `pip "
        "install` or `git worktree` command outputs.",
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
        "this purpose, but requires at minimum git 2.23. Setting this option to 'true' "
        "allows the use of older git versions for this purpose.",
    },
    "builder": {
        "name": "Name of the builder class used in pybm to manage "
        "virtual Python environments. If you want to supply your own custom builder "
        "class, set this value to your custom subclass of pybm.builders.BaseBuilder.",
        "homedir": "Optional home directory containing pre-built virtual environments. "
        "The default for pybm is to create the virtual environment directly into the "
        "new git worktree, but you can also choose to link existing environments, "
        "which are assumed to be subdirectories of this location.",
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
        "name": "Name of the runner class used in pybm to run "
        "benchmarks inside Python virtual environments. If you "
        "want to supply your own custom runner class, set this "
        "value to your custom subclass of pybm.runners.BaseRunner.",
        "failfast": "Whether to abort the benchmark process prematurely on the first "
        "encountered exception instead of continuing until completion.",
        "contextproviders": "A colon-separated list of context provider functions. "
        "In pybm benchmarks, context can be specified to include "
        "additional information in the resulting JSON files. "
        "A context provider function in pybm takes no arguments "
        "and returns two string values, which are used as key "
        "and value for the benchmark context object.",
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
