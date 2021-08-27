"""
Virtual environment creation class for benchmarking
with custom requirements in Python."""
import os
import shutil
from typing import List

from pybm.exceptions import VenvError
from pybm.subprocessing import CommandWrapperMixin

_venv_flags = {
    "venv": {
        "overwrite": {True: "--clear", False: None},
        "upgrade_deps": {True: "--upgrade-deps", False: None}
    },
    "pip": {

    },
}


class VenvBuilder(CommandWrapperMixin):
    """Virtual environment builder class."""

    def __init__(self):
        # either the venv is created in a special home directory or straight
        # into the worktree
        super().__init__(command_db=_venv_flags, exception_type=VenvError)
        self.venv_root = os.getenv("VENV_HOME", None)
        self.venv_paths = []

    def prepare_subprocess_args(self, executable: str, module: str, *args,
                                **kwargs):
        call_args = [executable, "-m", module, *args]
        # parse venv command line options separately
        call_args += self.parse_flags(**kwargs)
        return call_args

    def create_environment(self, executable: str, env_dir: str, **kwargs) -> \
            int:
        command = self.prepare_subprocess_args(executable, "venv", env_dir,
                                               **kwargs)
        new_env_path = os.path.join(self.venv_root, env_dir)
        self.venv_paths.append(new_env_path)
        return self.wrapped_subprocess_call("run", command, encoding="utf-8")

    @staticmethod
    def remove_environment(env_dir: str):
        shutil.rmtree(env_dir)

    def install_packages(self, package_list: List[str]):
        pass
