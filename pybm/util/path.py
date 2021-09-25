from pathlib import Path
from typing import Union, List

from pybm.util.common import lmap


def current_folder():
    return Path.cwd().resolve()


def get_subdirs(path: Union[str, Path]):
    p = Path(path).resolve()
    # All subdirectories in the current directory, not recursive.
    return [f.stem for f in filter(Path.is_dir, p.iterdir())]


def list_contents(path: Union[str, Path], file_suffix: str = "",
                  names_only: bool = True) -> List[str]:
    p = Path(path).resolve()
    glob_pattern = "*" if file_suffix == "" else "*" + file_suffix
    if names_only:
        return lmap(lambda x: str(x.name), p.glob(glob_pattern))
    else:
        return lmap(str, p.glob(glob_pattern))
