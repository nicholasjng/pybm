"""
Virtual environment creation class for benchmarking
with custom requirements in Python."""
import contextlib
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Union

import pybm.builders.util as builder_util
from pybm.builders.base import PythonEnvBuilder
from pybm.config import PybmConfig
from pybm.exceptions import BuilderError
from pybm.specs import PythonSpec
from pybm.util.common import version_string
from pybm.util.print import abbrev_home
from pybm.util.subprocess import run_subprocess


@contextlib.contextmanager
def action_context(action: str, directory: Union[str, Path]):
    try:
        fmt_action = action.capitalize()
        if fmt_action.endswith("e"):
            fmt_action = fmt_action[:-1]
        attr = "new" if action == "create" else "existing"
        print(f"{fmt_action}ing {attr} virtual environment in "
              f"location {abbrev_home(directory)}.....", end="")
        yield
        print("done.")
        if not action.endswith("e"):
            action += "e"
        print(f"Successfully {action}d {attr} virtual environment in location "
              f"{abbrev_home(directory)}.")
    except BuilderError:
        print("failed.")


@contextlib.contextmanager
def pip_context(action: str, packages: List[str], directory: Union[str, Path]):
    try:
        pkgs = ", ".join(packages)
        mode = "into" if action == "install" else "from"
        fmt_action = action.capitalize()
        print(f"{fmt_action}ing packages {pkgs} {mode} virtual "
              f"environment in location {directory}.....", end="")
        yield
        print("done.")
        print(f"Successfully {action}ed packages {pkgs} {mode} virtual "
              f"environment in location {directory}.")
    except BuilderError:
        print("failed.")


class VenvBuilder(PythonEnvBuilder):
    """Python standard library virtual environment builder class."""

    def __init__(self, config: PybmConfig):
        super().__init__(config=config)
        self.venv_home: str = config.get_value("builder.homeDirectory")

        # persistent venv options
        self.venv_options: List[str] = []
        venv_option_string: str = config.get_value(
            "builder.persistentVenvOptions")
        if venv_option_string != "":
            self.venv_options = venv_option_string.split(",")

        # persistent pip install options
        self.pip_install_options: List[str] = []
        pip_install_option_string: str = config.get_value(
            "builder.persistentPipInstallOptions")
        if pip_install_option_string != "":
            self.pip_install_options = pip_install_option_string.split(",")

        # persistent pip uninstall options
        self.pip_uninstall_options: List[str] = []
        pip_uninstall_option_string: str = config.get_value(
            "builder.persistentPipUninstallOptions")
        if pip_uninstall_option_string != "":
            self.pip_uninstall_options = \
                pip_uninstall_option_string.split(",")

    def add_arguments(self, command: str):
        if command == "create":
            args = [{"flags": "--python",
                     "type": str,
                     "default": sys.executable,
                     "dest": "python_executable",
                     "help": "Python interpreter to use in "
                             "virtual environment construction.",
                     "metavar": "<python>"},
                    {"flags": "--venv-options",
                     "nargs": "*",
                     "default": None,
                     "help": "Space-separated list of command "
                             "line options for virtual "
                             "environment creation using venv. "
                             "To get a comprehensive list of "
                             "options, run `python -m venv -h`.",
                     "metavar": "<options>"}]

        elif command == "install":
            args = [{"flags": "packages",
                     "nargs": "*",
                     "default": None,
                     "metavar": "<packages>",
                     "help": "Package dependencies to install "
                             "into the new virtual environment "
                             "using pip."},
                    {"flags": "-r",
                     "type": str,
                     "default": None,
                     "metavar": "<requirements>",
                     "dest": "requirements_file",
                     "help": "Requirements file for dependency "
                             "installation in the newly created "
                             "virtual environment."},
                    {"flags": "--pip-options",
                     "nargs": "*",
                     "default": None,
                     "help": "Space-separated list of command "
                             "line options for dependency "
                             "installation in the created"
                             "virtual environment using "
                             "`pip install`. To get a "
                             "comprehensive list of options, "
                             "run `python -m pip install -h`.",
                     "metavar": "<options>"}]
        elif command == "uninstall":
            args = [{"flags": "packages",
                     "nargs": "+",
                     "metavar": "<packages>",
                     "help": "Package dependencies to uninstall "
                             "from the benchmarking environment "
                             "using pip."},
                    {"flags": "--pip-options",
                     "nargs": "*",
                     "default": None,
                     "help": "Space-separated list of command "
                             "line options for dependency "
                             "removal in the benchmark "
                             "environment using "
                             "`pip uninstall`. To get a "
                             "comprehensive list of options, "
                             "run `python -m pip uninstall -h`.",
                     "metavar": "<options>"}]
        else:
            args = []
        return args

    def create(self,
               executable: Union[str, Path],
               destination: Union[str, Path],
               options: Optional[List[str]] = None,
               verbose: bool = False) -> PythonSpec:
        options = options or []
        # create the venv in the worktree or in a special home directory
        dest = Path(destination)
        if self.venv_home == "":
            env_dir = dest
        else:
            env_dir = (Path(self.venv_home) / dest.name).resolve()

        # THIS LINE IS EXTREMELY IMPORTANT. Resolve symlinks if the
        # given Python interpreter was a symlink to begin with.
        resolved_executable = Path(executable).resolve()

        command = [str(resolved_executable), "-m", "venv", str(env_dir)]
        options += self.venv_options
        # Prevent duplicate options
        command += list(set(options))

        with action_context("create", directory=env_dir):
            run_subprocess(command)

        executable = builder_util.get_executable(env_dir)
        python_version = version_string(
            builder_util.get_python_version(executable))
        return PythonSpec(root=str(env_dir),
                          executable=executable,
                          version=python_version,
                          packages=self.list_packages(executable))

    def delete(self, env_dir: Union[str, Path], verbose: bool = False) -> None:
        path = Path(env_dir)
        if not path.exists() or not path.is_dir():
            raise BuilderError(f"No virtual environment found at location"
                               f" {env_dir}: Location does not exist or is "
                               f"not a directory.")
        elif not builder_util.is_valid_venv(path):
            raise BuilderError(f"Given directory {env_dir} was not recognized "
                               f"as a valid virtual environment.")

        with action_context("remove", directory=env_dir):
            shutil.rmtree(env_dir)

    def link(self, env_dir: Union[str, Path], verbose: bool = False):
        with action_context("link", directory=env_dir):
            # TODO: This discovery stuff should go into caller routine
            if (Path(self.venv_home) / env_dir).exists():
                path = Path(self.venv_home) / env_dir
            else:
                path = Path(env_dir)
            if not builder_util.is_valid_venv(path, verbose=verbose):
                msg = f"The specified path {env_dir} was not recognized " \
                      f"as a valid virtual environment, since no `python`/" \
                      f"`pip` executables or symlinks were discovered."
                raise BuilderError(msg)
            executable = builder_util.get_executable(env_dir)
            python_version = version_string(
                builder_util.get_python_version(executable))
            packages = self.list_packages(executable, verbose=verbose)
            spec = PythonSpec(root=str(env_dir),
                              executable=executable,
                              version=python_version,
                              packages=packages)
            return spec

    def install_packages(self,
                         spec: PythonSpec,
                         packages: Optional[List[str]] = None,
                         requirements_file: Optional[str] = None,
                         options: Optional[List[str]] = None,
                         verbose: bool = False) -> None:
        options = options or []
        executable = spec.executable
        command = [executable, "-m", "pip", "install"]
        if packages is not None:
            pass
        elif requirements_file is not None:
            req_path = Path(requirements_file)
            if not req_path.exists() or not req_path.is_file():
                raise BuilderError(f"File {requirements_file!r} does not "
                                   f"exist or was not recognized as a file.")
            with open(req_path, "r") as req_file:
                packages = req_file.readlines()
        else:
            raise BuilderError("Either a package list or a requirements "
                               "file need to be specified to the install "
                               "command.")
        command += list(packages)
        options += self.pip_install_options
        options += [f"--find-links={loc}" for loc in self.wheel_caches]
        command += list(set(options))

        with pip_context("install", packages, spec.root):
            run_subprocess(command, ex_type=BuilderError)

        # this only runs if the subprocess succeeds
        new_packages = self.list_packages(executable=executable)
        spec.update_packages(packages=new_packages)

    def uninstall_packages(self,
                           spec: PythonSpec,
                           packages: List[str],
                           options: Optional[List[str]] = None,
                           verbose: bool = False) -> None:
        options = options or []
        options += self.pip_uninstall_options
        executable = spec.executable
        command = [executable, "-m", "pip", "uninstall", *packages]
        command += list(set(options))

        with pip_context("uninstall", packages, spec.root):
            run_subprocess(command)

        # this only runs if the subprocess succeeds
        new_packages = self.list_packages(executable=executable)
        spec.update_packages(packages=new_packages)

    def list_packages(self, executable: Union[str, Path],
                      verbose: bool = False) -> List[str]:
        command = [str(executable), "-m", "pip", "list", "--format=freeze"]
        # `pip list` output: table header, separator, package list
        # _, packages = flat_pkg_table[0], flat_pkg_table[2:]
        # return lmap(lambda x: "==".join(x.split()[:2]), packages)

        rc, pip_output = run_subprocess(command)

        return pip_output.splitlines()

    def is_linked_venv(self, spec: PythonSpec):
        root = Path(spec.root)
        if self.venv_home != "" and root.parent == Path(self.venv_home):
            return True
        return False
