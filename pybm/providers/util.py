import os
from pathlib import Path
from typing import Union, Tuple

from pybm.exceptions import ProviderError
from pybm.specs import PythonSpec
from pybm.util.common import version_tuple
from pybm.util.path import get_subdirs, get_filenames, walk
from pybm.util.subprocess import run_subprocess


def get_python_version(executable: str) -> Tuple[int, int, int]:
    cmd = "import sys; print('{0}.{1}.{2}'.format(*sys.version_info[:3]))"
    command = [executable, "-c", cmd]
    rc, output = run_subprocess(command, errors="ignore")
    if rc != 0:
        msg = f"Unable to get version from Python executable {executable}."
        raise ProviderError(msg)
    else:
        # strip away trailing newline from print statement
        return version_tuple(output.strip())


def get_executable(root: Union[str, Path]) -> str:
    path = Path(root)
    if os.name == "nt":
        return str(path / "Scripts" / "python.exe")
    else:
        return str(path / "bin" / "python")


def get_venv_root(executable: Union[str, Path]) -> Path:
    return Path(executable).parents[1]


def has_build_files(root: Union[str, Path], verbose: bool = False):
    build_files = ["setup.py", "pyproject.toml"]

    env_path = Path(root)

    for file in build_files:
        if (env_path / file).exists():
            return True
    return False


def is_valid_venv(path: Union[str, Path], verbose: bool = False) -> bool:
    """Check if a directory is a valid virtual environment."""
    path = Path(path)
    if not path.exists():
        return False

    subdirs = set(get_subdirs(path=path))
    if os.name != "nt":
        exec_set, bin_dir = {"pip", "python"}, "bin"
    else:
        exec_set, bin_dir = {"pip.exe", "python.exe"}, "Scripts"

    if verbose:
        print(
            f"Attempting to locate executable directory {bin_dir!r} in {path}.....",
            end="",
        )

    if bin_dir not in subdirs:
        if verbose:
            print("failed.")
            print(
                f"Expected to find a {bin_dir!r} directory containing `python/pip`"
                f"executables, but the directory does not exist."
            )
        return False

    if verbose:
        print("success.")

    # at minimum, pip and python executables / symlinks are required
    # TODO: Assert they are executables or symlinks to executables
    if verbose:
        print(
            f"Attempting to locate required executables in the {bin_dir!r} "
            f"subdirectory.....",
            end="",
        )

    actual_set = set(get_filenames(path / bin_dir))

    if not exec_set <= actual_set:
        if verbose:
            print("failed.")
            print(
                "The following required executables could not be located inside the "
                f"{bin_dir!r} directory: {', '.join(exec_set - actual_set)}"
            )
        return False

    if verbose:
        print("success.")
    return True


def is_linked_venv(home: str, spec: PythonSpec):
    root = get_venv_root(spec.executable)
    if home != "" and root.parent == Path(home):
        return True
    return False


def locate_requirements_file(path: Union[str, Path], absolute: bool = True):
    target_name = "requirements.txt"
    path = Path(path)

    if (path / target_name).exists():
        return path / target_name

    for pp in walk(path, absolute=absolute):
        # endswith assures the discovery of files with slightly different names
        # (e.g. {build,test}_requirements.txt)
        if pp.name.endswith(target_name):
            return pp
    return None
