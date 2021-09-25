"""
Virtual environment creation class for benchmarking
with custom requirements in Python."""
import os
import pathlib
import re
import shutil
import sys
from dataclasses import dataclass, field
from typing import List, Text, Optional

from pybm.util.common import lmap
from pybm.exceptions import EnvBuilderError
from pybm.util.path import get_subdirs, list_contents
from pybm.subprocessing import CommandWrapperMixin


@dataclass
class EnvSpec:
    root: str = field()
    executable: str = field()
    python_version: str = field()
    packages: List[str] = field(default_factory=list)


class PythonStdlibBuilder(CommandWrapperMixin):
    """Virtual environment builder class."""

    def __init__(self):
        super().__init__(exception_type=EnvBuilderError)
        self.venv_root = os.getenv("VENV_ROOT", "")

    def create(self, executable: str, destination: str,
               options: Optional[List[str]] = None) -> EnvSpec:
        # either the venv is created in a special home directory or right
        # in the worktree
        if self.venv_root == "":
            env_dir = os.path.join(destination, "venv")
        else:
            env_dir = os.path.join(self.venv_root,
                                   os.path.basename(destination))

        command = [executable, "-m", "venv", env_dir]
        if options is not None:
            command += options

        self.run_subprocess(command)

        executable = self.get_executable(env_dir)
        return EnvSpec(root=env_dir,
                       executable=executable,
                       python_version=self.get_python_version(executable),
                       packages=self.list_packages(executable))

    @staticmethod
    def delete(env_dir: str) -> None:
        shutil.rmtree(env_dir)

    def link_existing(self, env_dir: str):
        if self.venv_root == "":
            raise VenvBuilderError("linking an existing environment is only "
                                   "supported with a set VENV_ROOT "
                                   "environment variable pointing to a valid "
                                   "directory.")
        env_dir = os.path.join(self.venv_root, env_dir)
        if not self.is_valid_venv(env_dir):
            msg = f"the specified path {env_dir} was not recognized " \
                  f"as a valid virtual environment, since no `python`/" \
                  f"`pip` executables or symlinks were discovered."
            raise VenvBuilderError(msg)

        executable = os.path.join(env_dir, "bin", "python")
        return EnvSpec(root=env_dir,
                       executable=executable,
                       python_version=self.get_python_version(executable),
                       packages=self.list_packages(executable))

    def install_packages(self, root: str,
                         package_list: List[str] = None,
                         requirements_file: str = None,
                         pip_options: Optional[List[str]] = None,
                         verbose: bool = False) -> List[str]:
        executable = self.get_executable(root=root)
        command = [executable, "-m", "pip", "install"]
        if package_list is not None:
            command += package_list
        elif requirements_file is not None:
            command += ["-r", requirements_file]
        else:
            raise VenvBuilderError("either a package list or a requirements "
                                   "file need to be specified to the install "
                                   "command.")

        if pip_options is not None:
            command += pip_options

        if verbose:
            print("Installing...")

        self.run_subprocess(command)

        if verbose:
            if package_list:
                package_cs = ", ".join(package_list)
                msg = f"Installed packages {package_cs}."
            else:
                msg = f"Installed packages from requirements file " \
                      f"{requirements_file}."
            print(msg)

        return self.list_packages(executable=executable)

    def list_environments(self) -> List[str]:
        return get_subdirs(self.venv_root)

    @staticmethod
    def get_executable(root: str) -> str:
        if sys.platform == "win32":
            return os.path.join(root, "Scripts", "python.exe")
        else:
            return os.path.join(root, "bin", "python")

    def list_packages(self, executable: str) -> List[Text]:
        command = [executable, "-m", "pip", "list"]

        rc, pip_output = self.run_subprocess(command)

        flat_pkg_table = pip_output.splitlines()
        # `pip list` output: table header, separator, package list
        _, packages = flat_pkg_table[0], flat_pkg_table[2:]

        return lmap(lambda x: "==".join(x.split()[:2]), packages)

    def get_python_version(self, executable: str) -> Text:
        command = [executable, "--version"]
        rc, output = self.run_subprocess(command)

        version_match = re.search(r'([\d.]+)', output)
        if version_match is not None:
            version = version_match.group()
            return version
        else:
            msg = f"unable to get version from Python executable {executable}."
            raise VenvBuilderError(msg)

    @staticmethod
    def is_valid_venv(path: str):
        """Check if a directory is a valid virtual environment."""
        sub_dirs = get_subdirs(path=path)
        bin_folder = "bin" if os.name != "nt" else "Scripts"
        if set(sub_dirs) != {bin_folder, "include", "lib"}:
            return False
        bin_dir = pathlib.Path(path).joinpath(bin_folder)
        # at minimum, pip and python executables / symlinks are required
        # TODO: Assert they are executables or symlinks to executables
        if not {"pip", "python"} <= set(list_contents(bin_dir)):
            return False
        return True


venv_builder = PythonStdlibBuilder()
