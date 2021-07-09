"""
Virtual environment creation class for benchmarking
with custom requirements in Python."""
import subprocess
import shutil
import sys
from venv_utils import parse_venv_flags


class VirtualenvBuilder:
    """Virtual environment builder class."""
    def __init__(self):
        self.executable = sys.executable
        self.venv_paths = []

    def run_command(self, *args, **kwargs):
        command = [self.executable, "-m", "venv"]
        command.extend(list(args))
        command.extend(parse_venv_flags(**kwargs))
        return subprocess.check_output(command).decode("utf-8")

    def create_environment(self, env_dir: str, overwrite=False):
        self.run_command(env_dir, overwrite=overwrite)

    @staticmethod
    def remove_environment(env_dir: str):
        shutil.rmtree(env_dir)
