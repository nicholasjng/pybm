import itertools
import pathlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Union, Dict, List

import yaml

from pybm.exceptions import PybmError
from pybm.mixins import StateMixin
from pybm.specs import CoreGroup, BuilderGroup, RunnerGroup, GitGroup, ReporterGroup
from pybm.util.imports import import_from_module

__all__ = [
    "PybmConfig",
    "get_builder_class",
    "get_runner_class",
    "get_runner_requirements",
    "get_reporter_class",
    "get_all_names",
    "get_all_keys",
]

Descriptions = Dict[str, str]


@dataclass
class PybmConfig(StateMixin):
    core: CoreGroup = CoreGroup()
    git: GitGroup = GitGroup()
    builder: BuilderGroup = BuilderGroup()
    runner: RunnerGroup = RunnerGroup()
    reporter: ReporterGroup = ReporterGroup()

    @classmethod
    def load(cls, path: Union[str, pathlib.Path]):
        if isinstance(path, str):
            path = Path(path)

        if not path.exists() or not path.is_file():
            raise PybmError(
                f"Configuration file {path} does not exist. "
                f"Make sure to run `pybm init` before using pybm "
                f"to set up environments or run benchmarks."
            )

        with open(path, "r") as config_file:
            spec = yaml.load(config_file, Loader=yaml.FullLoader)

        return PybmConfig(
            core=CoreGroup(**spec["core"]),
            git=GitGroup(**spec["git"]),
            runner=RunnerGroup(**spec["runner"]),
            builder=BuilderGroup(**spec["builder"]),
            reporter=ReporterGroup(**spec["reporter"]),
        )

    def to_dict(self):
        return {
            "core": asdict(self.core),
            "git": asdict(self.git),
            "runner": asdict(self.runner),
            "builder": asdict(self.builder),
            "reporter": asdict(self.reporter),
        }

    def save(self, path: Union[str, pathlib.Path]):
        with open(path, "w") as config_file:
            yaml.dump(self.to_dict(), config_file)

    def describe(self, attr):
        current = self.get_value(attr)
        group, name = attr.split(".")
        annotations: Dict[str, type] = self.get_value(group + ".__annotations__")
        value_type = annotations[name].__name__

        print(f"Describing configuration option {attr!r}.")
        print(f"Value type:    {value_type}")
        print(f"Current value: {current!r}")
        print(
            description_db[group].get(
                name, f"No description available for {group} attribute {name}."
            )
        )


def get_builder_class(config: PybmConfig):
    class_name = import_from_module(config.get_value("builder.name"))
    return class_name(config)


def get_runner_class(config: PybmConfig):
    class_name = import_from_module(config.get_value("runner.name"))
    return class_name(config)


def get_reporter_class(config: PybmConfig):
    class_name = import_from_module(config.get_value("reporter.name"))
    return class_name(config)


def get_runner_requirements(config: PybmConfig) -> List[str]:
    return get_runner_class(config).required_packages


def get_all_names(cls) -> List[str]:
    return [k for k in vars(cls).keys() if not k.startswith("_")]


def get_all_keys(config: PybmConfig) -> List[str]:
    groups = get_all_names(config)
    names = [get_all_names(group) for group in groups]
    return list(itertools.chain.from_iterable(names))


description_db: Dict[str, Descriptions] = {
    "core": {
        "datefmt": "Datetime format string used to format "
        "timestamps for environment creation and "
        "modification. For a comprehensive list of "
        "identifiers and options, check the Python "
        "standard library documentation on datetime.strftime: "
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
        "createWorktreeInParentDirectory": "Whether to create worktrees "
        "in the parent directory of your git repository by default. "
        "Some IDEs may get confused when you initialize another "
        "git worktree inside your main repository, so this option "
        "provides a way to keep your main repo folder clean without having "
        "to explicitly type '../my-dir' every time you create a git worktree.",
    },
    "builder": {
        "name": "Name of the builder class used in pybm to manage "
        "virtual Python environments. If you want to supply "
        "your own custom builder class, set this value to "
        "your custom subclass of pybm.builders.BaseBuilder.",
        "homedir": "Optional home directory containing pre-built "
        "virtual environments. The default for pybm is to "
        "create the virtual environment directly into the new git worktree, "
        "but you can also choose to link existing environments, which are assumed "
        "to be subdirectories of this location.",
        "wheelcaches": "A string of local directories separated by "
        'colons (":"), like a Unix PATH variable,'
        "containing prebuilt wheels for Python packages. "
        "Set this if you request a package that has no "
        "wheels for your Python version or architecture "
        "available, and have to build target-specific "
        "wheels yourself.",
        "pipinstalloptions": "Comma-separated list of options "
        "passed to `pip install` in a "
        "pip-based builder. Set this if you "
        "use a number of `pip install` "
        "options consistently, and do not want "
        "to type them out in every call to "
        "`pybm env install`.",
        "pipuninstalloptions": "Comma-separated list of options "
        "passed to `pip uninstall` in a "
        "pip-based builder. Set this if you "
        "use a number of `pip uninstall` "
        "options consistently, and do not "
        "want to type them out in every "
        "call to `pybm env uninstall`.",
        "venvoptions": "Comma-separated list of options "
        "for virtual environment creation in a venv-based"
        "builder. Set this if you use a number "
        "of `python -m venv` options consistently, "
        "and do not want to type them out in every `pybm env create` call.",
    },
    "runner": {
        "name": "Name of the runner class used in pybm to run "
        "benchmarks inside Python virtual environments. If you "
        "want to supply your own custom runner class, set this "
        "value to your custom subclass of pybm.runners.BaseRunner.",
        "failfast": "",
        "contextproviders": "",
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
