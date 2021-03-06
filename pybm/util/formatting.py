from pathlib import Path
from typing import Iterable, List, Optional, Union

from pybm.util.common import lmap

_COLUMN_BREAK = "|"
_SPACE = " "
_SEPCHAR = "-"


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


def format_benchmark(name: str, path_to_file: str) -> str:
    python_file = Path(path_to_file)
    target_path = python_file.relative_to(python_file.parents[1])
    return str(target_path) + ":" + name


def format_floating(
    value: float, digits: int, std: Optional[float] = None, as_integers: bool = False
) -> str:

    if as_integers:
        if std is not None:
            res = f"{int(value)} ± {int(std)}"
        else:
            res = f"{int(value)}"
    else:
        if std is not None:
            res = f"{value:.{digits}f} ± {std:.{digits}f}"
        else:
            res = f"{value:.{digits}f}"

    return res


def format_ref(ref: str, commit: str, shalength: int):
    if ref != commit:
        # ref is branch / tag
        ref += f"@{commit[:shalength]}"
    else:
        # ref is commit, trim SHA to desired length
        ref = ref[:shalength]

    return ref


def format_relative(value: float, digits: int) -> str:
    return f"{value:+.{digits}%}"


def format_speedup(speedup: float, digits: int, as_integers: bool = False) -> str:
    return format_floating(speedup, digits=digits, as_integers=as_integers) + "x"


def make_line(values: Iterable[str], column_widths: Iterable[int], padding: int) -> str:
    pad_char = _SPACE * padding
    sep = _COLUMN_BREAK.join([pad_char] * 2)
    left_bound, right_bound = _COLUMN_BREAK + pad_char, pad_char + _COLUMN_BREAK

    line = sep.join(f"{n:<{w}}" for n, w in zip(values, column_widths))
    return left_bound + line + right_bound


def make_separator(column_widths: Iterable[int], padding) -> str:
    pad_char = _SPACE * padding
    sep = _COLUMN_BREAK.join([pad_char] * 2)
    left_bound, right_bound = _COLUMN_BREAK + pad_char, pad_char + _COLUMN_BREAK

    line_sep = sep.join(_SEPCHAR * w for w in column_widths)
    return left_bound + line_sep + right_bound
