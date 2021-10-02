import os
from typing import List, Iterable

from pybm.specs import BenchmarkEnvironment
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


def format_environments(environments: List[BenchmarkEnvironment],
                        padding: int = 1) -> None:

    column_names = ["Name", "Git ref", "Ref type", "Worktree directory",
                    "Python version"]
    env_data = [column_names]
    for env in environments:
        values = [env.get_value("name")]
        values.extend(env.worktree.get_ref_and_type())
        root: str = env.get_value("worktree.root")
        values.append(abbrev_home(root))
        values.append(env.get_value("python.version"))
        env_data.append(values)

    column_widths = calculate_column_widths(env_data)

    for i, d in enumerate(env_data):
        print(make_line(d, column_widths, padding=padding))
        if i == 0:
            print(make_separator(column_widths, padding=padding))
