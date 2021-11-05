import os
from pathlib import Path
from typing import Union, Tuple

from pybm.exceptions import BuilderError
from pybm.util.common import version_tuple
from pybm.util.path import get_subdirs, list_contents
from pybm.util.subprocess import run_subprocess


def get_python_version(executable: str) -> Tuple[int, int, int]:
    cmd = "import sys; print('{0}.{1}.{2}'.format(*sys.version_info[:3]))"
    command = [executable, "-c", cmd]
    rc, output = run_subprocess(command, errors="ignore")
    if rc != 0:
        msg = f"Unable to get version from Python executable {executable}."
        raise BuilderError(msg)
    else:
        # strip away trailing newline from print statement
        return version_tuple(output.strip())


def get_executable(root: Union[str, Path]) -> str:
    path = Path(root)
    if os.name == "nt":
        return str(path / "Scripts" / "python.exe")
    else:
        return str(path / "bin" / "python")


def is_valid_venv(path: Union[str, Path], verbose: bool = False) -> bool:
    """Check if a directory is a valid virtual environment."""
    subdir_set = set(get_subdirs(path=path))
    if os.name != "nt":
        exec_set, bin_folder = {"pip", "python"}, "bin"
    else:
        # TODO: Confirm the executable names on Windows
        exec_set, bin_folder = {"pip.exe", "python.exe"}, "Scripts"

    if verbose:
        print(
            f"Matching subdirectories of {path} against default "
            f"subdirectories of a virtual environment root.....",
            end="",
        )

    if bin_folder not in subdir_set:
        if verbose:
            print("failed.")
            print(
                f"Expected to find a {bin_folder!r} directory "
                f"containing the executables, but the directory does "
                f"not exist."
            )
        return False

    if verbose:
        print("success.")

    bin_dir = Path(path) / bin_folder

    # at minimum, pip and python executables / symlinks are required
    # TODO: Assert they are executables or symlinks to executables
    if verbose:
        print(
            f"Attempting to locate required executables in the "
            f"executable subfolder {bin_dir}.....",
            end="",
        )

    actual_set = set(list_contents(bin_dir))

    if not exec_set <= actual_set:
        if verbose:
            print("failed.")
            missing = ", ".join(exec_set - actual_set)
            print(
                "The following required executables could not be "
                f"located inside {bin_dir}: {missing}"
            )
        return False

    if verbose:
        print("successful.")
    return True
