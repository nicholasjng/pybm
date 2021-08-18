"""
Virtual environment creation class for benchmarking
with custom requirements in Python."""
import os
import subprocess
import shutil
import sys
from typing import List

from pybm.exceptions import VenvError

_venv_flags = {
    "overwrite": {True: "--clear", False: None},
    "upgrade_deps": {True: "--upgrade-deps", False: None}
}


class VenvBuilder:
    """Virtual environment builder class."""

    def __init__(self):
        self.executable = sys.executable
        self.venv_root = os.getenv("VENV_HOME", None)
        self.venv_paths = []

    @staticmethod
    def parse_flags(**kwargs) -> List[str]:
        flags = []
        for k, v in kwargs.items():
            if k not in _venv_flags:
                raise ValueError(f"unknown option {k} supplied.")
            options = _venv_flags[k]
            if v not in options:
                raise ValueError(f"unknown value {v} given for option {k}.")
            flag = options[v]
            if flag is not None:
                flags.append(flag)
        return flags

    def create_environment(self, env_dir: str, **kwargs):
        command = [self.executable, "-m", "venv", env_dir]
        command += self.parse_flags(**kwargs)
        new_env_path = os.path.join(os.getcwd(), env_dir)
        self.venv_paths.append(new_env_path)
        try:
            return subprocess.check_output(command).decode("utf-8")
        except subprocess.CalledProcessError as e:
            full_command = " ".join(command)
            msg = f"The command `{full_command}` returned the non-zero " \
                  f"exit code {e.returncode}. Further information (output of " \
                  f"the subprocess command):\n\n {e.output.decode()}"
            raise VenvError(msg)

    @staticmethod
    def remove_environment(env_dir: str):
        shutil.rmtree(env_dir)

    def install_packages(self, package_list: List[str]):
        pass
