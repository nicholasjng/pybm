from pathlib import Path
from typing import List, Iterable, Union

from pybm.util.common import lmap


def abbrev_home(path: Union[str, Path]) -> str:
    path = Path(path).resolve()
    try:
        homepath = path.relative_to(Path.home())
        abbrev_path = str(Path("~") / homepath)
    except ValueError:
        # case where the env path is not a subpath of the home directory
        abbrev_path = str(path)
    return abbrev_path


def calculate_column_widths(data: Iterable[Iterable[str]]) -> List[int]:
    data_lengths = zip(*(lmap(len, d) for d in data))
    return lmap(max, data_lengths)


def make_line(values: Iterable[str], column_widths: Iterable[int], padding: int) -> str:
    pad_char = " " * padding
    sep = "|".join([pad_char] * 2)

    line = pad_char + sep.join(f"{n:<{w}}" for n, w in zip(values, column_widths))
    return line


def make_separator(column_widths: Iterable[int], padding) -> str:
    return "+".join("-" * (w + 2 * padding) for w in column_widths)
