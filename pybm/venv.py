"""
Virtual environment creation class for benchmarking with custom requirements in Python.
"""
import contextlib
import shutil
import warnings
from pathlib import Path
from typing import List, Optional, Tuple, Union

from pybm.exceptions import PybmError
from pybm.util.common import version_string
from pybm.util.formatting import abbrev_home
from pybm.util.subprocess import run_subprocess
from pybm.util.venv import (
    get_executable,
    get_python_version,
    get_venv_root,
    has_build_files,
    is_valid_venv,
    locate_requirements_file,
)


@contextlib.contextmanager
def action_context(action: str, directory: Union[str, Path]):
    try:
        new_or_existing = "new" if action == "create" else "existing"
        if action.endswith("e"):
            action = action[:-1]
        print(
            f"{action.capitalize()}ing {new_or_existing} virtual environment in "
            f"location {abbrev_home(directory)}.....",
            end="",
        )
        yield
        print("done.")
        print(
            f"Successfully {action}ed {new_or_existing} virtual environment in "
            f"location {abbrev_home(directory)}."
        )
    except PybmError:
        print("failed.")
        raise


@contextlib.contextmanager
def pip_context(
    action: str,
    executable: Union[str, Path],
    packages: Optional[List[str]] = None,
    requirements_file: Optional[str] = None,
):
    try:
        if packages is None:
            resource = f"from requirements file {requirements_file!r}"
        else:
            resource = ", ".join(packages)

        root = get_venv_root(executable)
        into_or_from = "into" if action in ["add", "install"] else "from"

        if action.endswith("e"):
            action = action[:-1]
        print(
            f"{action.capitalize()}ing packages {resource} {into_or_from} virtual "
            f"environment in location {abbrev_home(root)}.....",
            end="",
        )
        yield
        print("done.")
        print(
            f"Successfully {action}ed packages {resource} {into_or_from} virtual "
            f"environment in location {abbrev_home(root)}."
        )
    except PybmError:
        print("failed.")
        raise


class PythonVenv:
    """Class representing a Python virtual environment."""

    def __init__(
        self,
        directory: Union[str, Path],
        executable: str,
        version: str = None,
        packages: List[str] = None,
        locations: List[str] = None,
    ):
        # prefix for virtual environment folders (name)
        self.prefix: str = "venv"
        self.directory = Path(directory)
        self.executable = executable
        self.version = version
        self.packages = packages or []
        self.locations = locations or []

    def add(
        self,
        packages: List[str],
        options: Optional[List[str]] = None,
    ):

        command = [self.executable, "-m", "pip", "install", *packages]

        # prepare options and extra pip install flags
        if options:
            command += options

        with pip_context("add", self.executable, packages=packages):
            run_subprocess(command)

        return self

    def create(
        self,
        options: Optional[List[str]] = None,
        in_tree: bool = False,
        verbose: bool = False,
    ):
        if in_tree:
            self.directory = self.directory / self.prefix
        else:
            self.directory = self.directory

        if self.directory.exists():
            if not is_valid_venv(self.directory, verbose=verbose):
                raise PybmError(
                    f"The specified path {str(self.directory)} is not a valid virtual "
                    f"environment, since no `python`/`pip` executables or symlinks "
                    f"were found."
                )

            with action_context("link", directory=self.directory):
                self.executable = get_executable(self.directory)
                self.version = version_string(get_python_version(self.executable))
                self.packages, self.locations = self.list()

                return self
        else:
            # THIS LINE IS EXTREMELY IMPORTANT. Resolve symlinks if the given Python
            # interpreter was a symlink to begin with.
            python = str(Path(self.executable).resolve())

            command = [python, "-m", "venv", str(self.directory)]

            if options:
                command += options

            with action_context("create", directory=self.directory):
                run_subprocess(command)

                self.executable = get_executable(self.directory)
                self.version = version_string(get_python_version(self.executable))
                self.packages, self.locations = self.list()

            return self

    def delete(self) -> None:
        path = get_venv_root(self.executable)

        if not path.exists():
            raise PybmError(f"Location {path} does not exist.")
        elif not path.is_dir():
            raise PybmError(f"Location {path} is not a directory.")
        elif not is_valid_venv(path):
            raise PybmError(
                f"Location {path} is not a valid virtual Python environment."
            )

        with action_context("remove", directory=path):
            shutil.rmtree(path)

    def install(
        self,
        directory: Union[str, Path],
        with_dependencies: bool = True,
        extra_packages: Optional[List[str]] = None,
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ):

        requirements_file = locate_requirements_file(directory, True)

        command = [self.executable, "-m", "pip", "install"]

        has_requirements = requirements_file is not None

        if has_requirements and with_dependencies:
            command += ["-r", str(requirements_file)]
        else:
            if not with_dependencies:
                msg = "Skipping dependency installation as the '--no-deps' option "
                "was specified."
            else:
                msg = "No requirements file found, skipping dependency installation."

            warnings.warn(msg)

        # check for existing setup.py/pyproject.toml in the directory.
        build_files = has_build_files(directory)

        if build_files:
            # install package at current ref in editable mode
            command += ["-e", str(directory)]
        else:
            warnings.warn(
                "Neither setup.py nor pyproject.toml build files were found. "
                "Skipping project installation."
            )

        # false <-> None or empty list
        has_extra_packages = bool(extra_packages)

        if not any([has_requirements, build_files, has_extra_packages]):
            warnings.warn(
                "All installation was skipped since neither requirements file, "
                "build files nor extra packages were given."
            )
            return self

        if extra_packages:
            command += extra_packages
        if options:
            command += options

        with pip_context(
            "install", self.executable, requirements_file=requirements_file
        ):
            run_subprocess(command)

        return self

    def list(self) -> Tuple[List[str], List[str]]:
        if self.executable == "" or not Path(self.executable).exists():
            return [], []

        command = [self.executable, "-m", "pip", "list"]

        rc, pip_output = run_subprocess(command)

        # `pip list` output: table header, separator, package list
        flat_pkg_table = pip_output.splitlines()[2:]
        packages, locations = [], []

        for line in flat_pkg_table:
            # TODO: When using pybm.Packages here, change to --format=json to parse
            #  directly
            split_line = line.split()
            packages.append("==".join(split_line[:2]))
            if len(split_line) > 2:
                locations.append(split_line[2])

        return packages, locations

    def remove(
        self,
        packages: List[str],
        options: Optional[List[str]] = None,
    ):

        options = options or []

        # do not ask for confirmation with -y switch
        command = [self.executable, "-m", "pip", "uninstall", "-y", *packages, *options]

        with pip_context("remove", self.directory, packages=packages):
            run_subprocess(command)

        return self

    def update(self):
        packages, locations = self.list()
        # preserve list object IDs
        self.packages.clear()
        self.packages.extend(packages)
        self.locations.clear()
        self.locations.extend(locations)
        return self
