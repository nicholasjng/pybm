import os
from pathlib import Path
from typing import List, Iterable, Union

from pybm.util.common import lmap


def abbrev_home(path: Union[str, Path]) -> str:
    str_path = str(path)
    home_dir = os.getenv("HOME")
    if home_dir is not None and str_path.startswith(home_dir):
        str_path = str_path.replace(home_dir, "~")
    return str_path


def calculate_column_widths(data: Iterable[Iterable[str]]) -> List[int]:
    data_lengths = zip(*(lmap(len, d) for d in data))
    return lmap(max, data_lengths)


def make_line(values: Iterable[str], column_widths: Iterable[int], padding: int) -> str:
    pad_char = " " * padding
    sep = "|".join([pad_char] * 2)
    offset = pad_char

    line = offset + sep.join(f"{n:<{w}}" for n, w in zip(values, column_widths))
    return line


def make_separator(column_widths: Iterable[int], padding) -> str:
    return "+".join("-" * (w + 2 * padding) for w in column_widths)
