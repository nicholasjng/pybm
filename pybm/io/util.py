from pathlib import Path
from typing import Union

from pybm.util.path import get_subdirs


def get_rundir(result_dir: Union[str, Path]) -> Path:
    # int key prevents unexpected sorting results for more than 10
    # directories (order 1 -> 10 -> 2 -> 3 ...)
    subdirs = sorted(get_subdirs(result_dir), key=int)

    folder = str(len(subdirs) + 1)

    result_path = Path(result_dir) / folder

    return result_path


def create_subdir(result_dir: Union[str, Path], ref: str) -> Path:
    ref = ref.replace("/", "-")

    result_subdir = Path(result_dir) / ref
    result_subdir.mkdir(parents=False, exist_ok=False)

    return result_subdir
