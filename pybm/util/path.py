from pathlib import Path
from typing import Union, List, Optional

from pybm.util.common import lmap


def current_folder():
    return Path.cwd().resolve()


def get_subdirs(path: Union[str, Path]):
    p = Path(path).resolve()
    # All subdirectories in the current directory, not recursive.
    return [f.stem for f in filter(Path.is_dir, p.iterdir())]


def list_contents(
    path: Union[str, Path],
    file_suffix: str = "",
    rel_path: Optional[str] = None,
    names_only: bool = False,
) -> List[str]:

    resolved_path = Path(path).resolve()

    glob_pattern = "*" if file_suffix == "" else "*" + file_suffix
    matching_files = resolved_path.glob(glob_pattern)

    if names_only:
        return lmap(lambda x: x.name, matching_files)
    elif rel_path is not None:
        return lmap(
            lambda p: str(p.relative_to(rel_path)), matching_files  # type: ignore
        )
    else:
        return lmap(str, matching_files)
