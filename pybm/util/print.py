import os
from typing import List, Iterable

from pybm.specs import BenchmarkEnvironment
from pybm.util.common import lmap


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
                        padding: int = 1):
    env_data = []
    column_names = ["Name", "Git ref", "Ref type", "Worktree directory",
                    "Python version"]
    for env in environments:
        values = [env.get_value("name")]
        values.extend(env.worktree.get_ref_and_type())
        root: str = env.get_value("worktree.root")
        home_dir = os.getenv("HOME")
        if home_dir is not None and root.startswith(home_dir):
            root = root.replace(home_dir, "~")
        values.append(root)
        values.append(env.get_value("python.version"))
        env_data.append(dict(zip(column_names, values)))

    column_widths = lmap(
        lambda name: max(max(len(name), len(val[name])) for val in env_data),
        column_names)

    print(make_line(column_names, column_widths, padding=padding))
    print(make_separator(column_widths, padding=padding))
    for d in env_data:
        print(make_line(d.values(), column_widths, padding=padding))
