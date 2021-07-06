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

    def run_command(self, *args, **kwargs):
        call_args = [self.executable, "-m", "venv"]
        call_args += list(args)
        call_args += parse_venv_flags(**kwargs)
        return subprocess.check_output(call_args).decode("utf-8")

    def create(self, env_dir: str, overwrite=False):
        self.run_command(env_dir, overwrite=overwrite)

    @staticmethod
    def remove(env_dir: str):
        shutil.rmtree(env_dir)
