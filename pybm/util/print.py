import os
from typing import List, Iterable

from pybm.util.common import lmap


def abbrev_home(path: str) -> str:
    home_dir = os.getenv("HOME")
    if home_dir is not None and path.startswith(home_dir):
        path = path.replace(home_dir, "~")
    return path


def calculate_column_widths(data: Iterable[Iterable[str]]) -> List[int]:
    data_lengths = zip(*(lmap(len, d) for d in data))
    return lmap(max, data_lengths)


def make_line(values: Iterable[str], column_widths: Iterable[int],
              padding: int) -> str:
    pad_char = " " * padding
    sep = "|".join([pad_char] * 2)
    offset = pad_char

    line = offset + sep.join(
        f"{n:<{w}}" for n, w in zip(values, column_widths)
    )
    return line


def make_separator(column_widths: Iterable[int], padding) -> str:
    return "+".join("-" * (w + 2 * padding) for w in column_widths)
