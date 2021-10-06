import os
from pathlib import Path
from typing import Optional, List, Union, Tuple

from pybm import PybmConfig
from pybm.exceptions import BuilderError
from pybm.mixins import SubprocessMixin
from pybm.specs import PythonSpec
from pybm.util.common import version_tuple
from pybm.util.path import get_subdirs, list_contents


class PythonEnvBuilder(SubprocessMixin):
    """Base class for all Python virtual environment builders."""

    def __init__(self, config: PybmConfig):
        super().__init__()
        self.ex_type = BuilderError
        self.wheel_caches = []
        wheel_cache_string: str = config.get_value(
            "builder.localWheelCaches")
        if wheel_cache_string != "":
            self.wheel_caches = wheel_cache_string.split(":")

    def create(self,
               executable: Union[str, Path],
               destination: Union[str, Path],
               options: Optional[List[str]] = None,
               verbose: bool = False) -> PythonSpec:
        raise NotImplementedError

    def delete(self, env_dir: Union[str, Path], verbose: bool = False) -> None:
        raise NotImplementedError

    def link_existing(self, env_dir: Union[str, Path],
                      verbose: bool = False) -> PythonSpec:
        raise NotImplementedError

    def install_packages(self,
                         spec: PythonSpec,
                         packages: Optional[List[str]] = None,
                         requirements_file: Optional[str] = None,
                         options: Optional[List[str]] = None,
                         verbose: bool = False) -> None:
        raise NotImplementedError

    def uninstall_packages(self,
                           spec: PythonSpec,
                           packages: List[str],
                           options: Optional[List[str]] = None,
                           verbose: bool = False) -> None:
        raise NotImplementedError

    def list_packages(self, executable: Union[str, Path],
                      verbose: bool = False):
        raise NotImplementedError

    def get_python_version(self,
                           executable: str) -> Tuple[int, int, int]:
        cmd = "import sys; print('{0}.{1}.{2}'.format(*sys.version_info[:3]))"
        command = [executable, "-c", cmd]
        rc, output = self.run_subprocess(command, print_status=False)
        if rc != 0:
            msg = f"Unable to get version from Python executable {executable}."
            raise BuilderError(msg)
        else:
            # strip away trailing newline from print statement
            return version_tuple(output.strip())

    @staticmethod
    def get_executable(root: Union[str, Path]) -> str:
        path = Path(root)
        if os.name == "nt":
            return str(path / "Scripts" / "python.exe")
        else:
            return str(path / "bin" / "python")

    @staticmethod
    def is_valid_venv(path: Union[str, Path], verbose: bool = False) -> bool:
        """Check if a directory is a valid virtual environment."""
        subdir_set = set(get_subdirs(path=path))
        if os.name != "nt":
            exec_set, bin_folder = {"pip", "python"}, "bin"
        else:
            # TODO: Confirm the executable names on Windows
            exec_set, bin_folder = {"pip.exe", "python.exe"}, "Scripts"
        if verbose:
            print(f"Matching subdirectories of {path} against default "
                  f"subdirectories of a virtual environment root.....",
                  end="")
        if bin_folder not in subdir_set:
            if verbose:
                print("failed.")
                print(f"Expected to find a {bin_folder!r} directory "
                      f"containing the executables, but the directory does "
                      f"not exist.")
            return False
        if verbose:
            print("successful.")
        bin_dir = Path(path) / bin_folder
        # at minimum, pip and python executables / symlinks are required
        # TODO: Assert they are executables or symlinks to executables
        if verbose:
            print(f"Attempting to locate required executables in the "
                  f"executable subfolder {bin_dir}.....", end="")
        actual_set = set(list_contents(bin_dir))
        if not exec_set <= actual_set:
            if verbose:
                print("failed.")
                missing = ", ".join(exec_set - actual_set)
                print("The following required executables could not be "
                      f"located inside {bin_dir}: {missing}")
            return False
        if verbose:
            print("successful.")
        return True
