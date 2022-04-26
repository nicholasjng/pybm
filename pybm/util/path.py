from pathlib import Path
from typing import Union, List, Optional

from pybm.util.common import lmap


def current_folder() -> Path:
    return Path.cwd().resolve()


def get_subdirs(path: Union[str, Path], absolute: bool = False) -> List[str]:
    p = Path(path)
    if absolute:
        p = p.resolve()

    # All subdirectories in the current directory, not recursive.
    return [f.stem for f in filter(Path.is_dir, p.iterdir())]


def get_filenames(
    path: Union[str, Path], file_ext: str = "", absolute: bool = False
) -> List[str]:
    p = Path(path)
    if absolute:
        p = p.resolve()

    filtered = filter(lambda x: x.is_file() and x.suffix == file_ext, p.iterdir())

    return [f.name for f in filtered]


def lsdir(
    path: Union[str, Path],
    glob_pattern: Optional[str] = None,
    file_suffix: str = "",
    relative_to: Optional[str] = None,
    include_subdirs: bool = False,
) -> List[Path]:

    resolved_path = Path(path).resolve()

    glob_pattern = glob_pattern or "*" + file_suffix

    if include_subdirs:
        glob_pattern = "**/" + glob_pattern

    assert isinstance(glob_pattern, str)

    matching_files = resolved_path.glob(glob_pattern)

    if relative_to is not None:
        return lmap(
            lambda p: p.relative_to(relative_to), matching_files  # type: ignore
        )
    else:
        return list(matching_files)


def walk(path: Union[str, Path], absolute: bool = False):
    for p in Path(path).iterdir():
        if p.is_dir():
            # defer to nested routine for the next directory
            yield from walk(p, absolute=absolute)
            continue
        # yield complete path
        yield p.resolve() if absolute else p
