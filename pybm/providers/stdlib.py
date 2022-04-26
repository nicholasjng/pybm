"""
Virtual environment creation class for benchmarking with custom requirements in Python.
"""
import contextlib
import os
import shutil
import warnings
from pathlib import Path
from typing import List, Optional, Union

import pybm.providers.util as builder_util
from pybm.exceptions import ProviderError
from pybm.providers.base import BaseProvider
from pybm.config import config
from pybm.specs import PythonSpec
from pybm.util.common import version_string
from pybm.util.formatting import abbrev_home
from pybm.util.subprocess import run_subprocess
from pybm.workspace import Workspace


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
    except ProviderError:
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

        root = builder_util.get_venv_root(executable)
        into_or_from = "into" if action in ["add", "install"] else "from"
        print(
            f"{action.capitalize()}ing packages {resource} {into_or_from} virtual "
            f"environment in location {str(root)}.....",
            end="",
        )
        yield
        print("done.")
        print(
            f"Successfully {action}ed packages {resource} {into_or_from} virtual "
            f"environment in location {str(root)}."
        )
    except ProviderError:
        print("failed.")
        raise


class PythonVenvProvider(BaseProvider):
    """Python standard library virtual environment builder class."""

    def __init__(self, name="venv"):
        super().__init__(name=name)

        # prefix for virtual environment folders (name)
        self.prefix: str = "venv"

        # alternative home directory for virtual environments
        # precedence: env-variable -> config value
        self.venv_home: str = os.getenv("PYBM_VENV_HOME", "")

        if self.venv_home == "":
            self.venv_home = config.get_value("provider.homedir")

    def add(
        self,
        workspace: Workspace,
        packages: List[str],
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> None:
        # prepare options and extra pip install flags
        options = options or []
        python = workspace.executable

        command = [python, "-m", "pip", "install", *packages, *options]

        with pip_context("add", python, packages=packages):
            run_subprocess(command, ex_type=self.ex_type)

    def create(
        self,
        executable: Union[str, Path],
        destination: Union[str, Path],
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> PythonSpec:

        options = options or []
        destination = Path(destination) / self.prefix

        # create the venv in a special home directory
        if self.venv_home != "":
            dest = str((Path(self.venv_home) / destination.name).resolve())
        else:
            dest = str(destination)

        # THIS LINE IS EXTREMELY IMPORTANT. Resolve symlinks if the given Python
        # interpreter was a symlink to begin with.
        resolved_executable = Path(executable).resolve()

        command = [str(resolved_executable), "-m", "venv", dest, *options]

        with action_context("create", directory=dest):
            run_subprocess(command)

        executable = builder_util.get_executable(dest)
        python_version = version_string(builder_util.get_python_version(executable))

        return PythonSpec(executable=executable, version=python_version)

    def delete(self, spec: PythonSpec, verbose: bool = False) -> None:
        path = builder_util.get_venv_root(spec.executable)

        if not path.exists() or not path.is_dir():
            raise self.ex_type(f"Location {path} does not exist or is not a directory.")
        elif not builder_util.is_valid_venv(path):
            raise self.ex_type(
                f"Given directory {path} is not a valid virtual environment."
            )

        with action_context("remove", directory=path):
            shutil.rmtree(path)

    def install(
        self,
        workspace: Workspace,
        extra_packages: Optional[List[str]] = None,
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> None:

        root, name, python = workspace.root, workspace.name, workspace.executable

        requirements_file = builder_util.locate_requirements_file(root, True)

        command = [python, "-m", "pip", "install"]

        has_requirements = requirements_file is not None

        if has_requirements:
            command += ["-r", str(requirements_file)]
        else:
            warnings.warn(
                f"No requirements file was found in the benchmark workspace {name!r}. "
                f"Skipping dependency installation."
            )

        # check for existing setup.py/pyproject.toml in the repo root.
        has_build_files = builder_util.has_build_files(root, verbose=verbose)

        if has_build_files:
            # install package at current ref in editable mode
            command += ["-e", str(root)]
        else:
            warnings.warn(
                f"Neither setup.py nor pyproject.toml build files were found for "
                f"benchmark workspace {name!r}. Skipping project installation."
            )

        # false <-> None or empty list
        has_extra_packages = bool(extra_packages)

        if not any([has_requirements, has_build_files, has_extra_packages]):
            warnings.warn(
                "All installation was skipped since neither requirements file, "
                "build files nor extra packages were given."
            )
            return

        if extra_packages:
            command += extra_packages
        if options is not None:
            command += options

        with pip_context("install", python, requirements_file=requirements_file):
            run_subprocess(command, ex_type=self.ex_type)

    def link(self, path: Union[str, Path], verbose: bool = False) -> PythonSpec:
        if self.venv_home != "":
            path = Path(self.venv_home) / Path(path).name
        else:
            path = Path(path) / self.prefix

        if not builder_util.is_valid_venv(path, verbose=verbose):
            msg = (
                f"The specified path {str(path)} was not recognized as a valid "
                f"virtual environment, since no `python`/`pip` executables or symlinks "
                f"were discovered."
            )
            raise self.ex_type(msg)

        with action_context("link", directory=path):
            executable = builder_util.get_executable(path)
            version = builder_util.get_python_version(executable)

        return PythonSpec(executable=executable, version=version_string(version))

    def remove(
        self,
        workspace: Workspace,
        packages: List[str],
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> None:

        options = options or []
        python = workspace.executable

        # do not ask for confirmation with -y switch
        command = [python, "-m", "pip", "uninstall", "-y", *packages, *options]

        with pip_context("remove", workspace.root, packages=packages):
            run_subprocess(command)
