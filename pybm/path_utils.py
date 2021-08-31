import pathlib
from pathlib import Path
from typing import Union, List, Text

from pybm.git_utils import lmap


def current_folder_name() -> str:
    return Path.cwd().stem


def get_subdirs(path: str):
    p = pathlib.Path(path).resolve()
    # All subdirectories in the current directory, not recursive.
    return [f.stem for f in filter(Path.is_dir, p.iterdir())]


def list_contents(path: Union[str, pathlib.Path], file_suffix: str = "",
                  names_only: bool = True) -> List[Text]:
    if isinstance(path, str):
        p = pathlib.Path(path).resolve()
    else:
        p = path
    glob_pattern = "*" if file_suffix == "" else "*" + file_suffix
    if names_only:
        return lmap(lambda x: str(x.stem), p.glob(glob_pattern))
    else:
        return lmap(str, p.glob(glob_pattern))
