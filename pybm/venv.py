"""
Virtual environment creation class for benchmarking
with custom requirements in Python."""
import os
import pathlib
import re
import shutil
from typing import List, Dict, Text, Union, Sequence

from pybm.exceptions import VenvBuilderError
from pybm.git_utils import lmap
from pybm.path_utils import get_subdirs, list_contents
from pybm.status_codes import SUCCESS
from pybm.subprocessing import CommandWrapperMixin

EnvSpec = Dict[Text, Union[Text, Sequence[Text]]]

_venv_options = ["--system-site-packages", "--symlinks", "--copies",
                 "--clear", "--upgrade", "--without-pip", "--upgrade-deps"]


class PythonStdlibBuilder(CommandWrapperMixin):
    """Virtual environment builder class."""

    def __init__(self):
        # either the venv is created in a special home directory or straight
        # into the worktree
        super().__init__(exception_type=VenvBuilderError)
        self.venv_root = os.getenv("VENV_HOME", "")

    @staticmethod
    def split_option_string(option_string: str) -> List[Text]:
        # Check both comma- and space-separated options
        for sep in [" ", ","]:
            option_list = option_string.split(sep)
            if all(opt in _venv_options for opt in option_list):
                return option_list
            else:
                continue

        eligible_options = ", ".join(_venv_options)
        msg = f"Failed parsing option string {option_string}. One or more " \
              f"arguments were not recognized as command line options for " \
              f"venv. Eligible options are: {eligible_options}"
        raise VenvBuilderError(msg)

    def make_env_spec(self, env_dir: str, executable: str) -> EnvSpec:
        env_spec = {"path": env_dir,
                    "python_version": self.get_python_version(executable),
                    "packages": self.list_packages(executable)}
        return env_spec

    def create(self, executable: str, destination: str,
               option_string: str = None) -> EnvSpec:

        if self.venv_root == "":
            env_dir = os.path.join(destination, "venv")
        else:
            env_dir = os.path.join(self.venv_root,
                                   os.path.basename(destination))

        command = [executable, "-m", "venv", env_dir]
        if option_string is not None:
            command += self.split_option_string(option_string)

        self.run_subprocess(command)

        return self.make_env_spec(env_dir, executable)

    @staticmethod
    def remove(env_dir: str) -> int:
        shutil.rmtree(env_dir)

        return SUCCESS

    def link_existing(self, env_dir: str):
        if not self.is_valid_venv(env_dir):
            msg = f"the specified path {env_dir} was not recognized " \
                  f"as a valid virtual environment, since no `python` or " \
                  f"`pip` executables / symlinks were discovered."
            raise VenvBuilderError(msg)

        executable = os.path.join(env_dir, "bin", "python")
        env_spec = {"path": env_dir,
                    "python_version": self.get_python_version(executable),
                    "packages": self.list_packages(executable)}
        return env_spec

    def install_packages(self, executable: str,
                         package_list: List[str] = None,
                         requirements_file: str = None,
                         pip_options: str = None) -> int:
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
            command += pip_options.split(",")

        self.run_subprocess(command)

        return SUCCESS

    def list_packages(self, executable: str) -> List[Text]:
        command = [executable, "-m", "pip", "list"]

        rc, pip_output = self.run_subprocess(command)

        flat_pkg_table = pip_output.splitlines()
        # `pip list` output: table header, separator, package list
        _, packages = flat_pkg_table[0], flat_pkg_table[2:]

        return lmap(lambda x: "==".join(x.split()), packages)

    def get_python_version(self, executable: str) -> Text:
        command = [executable, "--version"]
        rc, output = self.run_subprocess(command)

        version_string = re.search(r'([\d.]+)', output)
        if version_string is not None:
            version = version_string.group()
            return version
        else:
            msg = f"unable to get version from Python executable {executable}."
            raise VenvBuilderError(msg)

    @staticmethod
    def is_valid_venv(path: str):
        """Check if a directory is a valid virtual environment."""
        sub_dirs = get_subdirs(path=path)
        assert sub_dirs == ["bin", "include", "lib"]
        bin_dir = pathlib.Path(path).joinpath("bin")
        # at minimum pip and python executable copies / symlinks are required
        # TODO: Assert they are executables or symlinks to executables
        assert {"pip", "python"} <= set(list_contents(bin_dir))


venv_builder = PythonStdlibBuilder()
