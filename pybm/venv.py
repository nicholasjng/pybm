"""
Virtual environment creation class for benchmarking
with custom requirements in Python."""
import os
import shutil
from typing import List, Dict, Text

from pybm.exceptions import VenvBuilderError
from pybm.subprocessing import CommandWrapperMixin
from pybm.venv_utils import split_option_string, get_python_version

EnvSpec = Dict[Text, Text]


class VenvBuilder(CommandWrapperMixin):
    """Virtual environment builder class."""

    def __init__(self):
        # either the venv is created in a special home directory or straight
        # into the worktree
        super().__init__(command_db={}, exception_type=VenvBuilderError)
        self.venv_root = os.getenv("VENV_HOME", "")
        self.venv_paths = []

    def create_environment(self, executable: str, destination: str,
                           option_string: str) -> EnvSpec:

        if self.venv_root == "":
            env_dir = os.path.join(destination, "venv")
        else:
            env_dir = os.path.join(self.venv_root,
                                   os.path.basename(destination))

        command = [executable, "-m", "venv", env_dir]
        command += split_option_string(option_string=option_string)

        self.wrapped_subprocess_call("run", command, encoding="utf-8")

        env_spec = {"path": env_dir,
                    "python_version": get_python_version(executable)}
        return env_spec

    @staticmethod
    def remove_environment(env_dir: str):
        shutil.rmtree(env_dir)

    def install_packages(self, executable: str, package_list: List[str]):
        pass


venv_builder = VenvBuilder()
