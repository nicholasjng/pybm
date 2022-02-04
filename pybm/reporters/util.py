import collections
from pathlib import Path
from statistics import mean, pstdev
from typing import Tuple, List, Dict, Any, Union

from pybm.util.common import tmap, lmap, partition_n, lfilter, split_list
from pybm.util.print import make_line, make_separator

# metric time unit prefix table
unit_table = {
    "s": 1.0,
    "sec": 1.0,
    "ms": 1e-3,
    "msec": 1e-3,
    "us": 1e-6,
    "usec": 1e-6,
    "ns": 1e-9,
    "nsec": 1e-9,
}

PRIVILEGED_COLUMNS = ["name", "reference", "speedup", "iterations", "repetitions"]


def format_benchmark(name: str, path_to_file: str) -> str:
    python_file = Path(path_to_file)
    target_path = python_file.relative_to(python_file.parents[1])
    return str(target_path) + ":" + name


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


def format_speedup(speedup: float, digits: int) -> str:
    return f"{speedup:.{digits}f}x"


def format_time(time: Tuple[float, float], time_unit: str, digits: int) -> str:
    tval, std = time

    if time_unit.startswith("ns"):
        # formatting nsecs as ints is nicer
        res = f"{int(tval)} ± {int(std)}"
    else:
        res = f"{tval:.{digits}f} ± {std:.{digits}f}"

    return res


def get_unique(attr: Union[str, List[str]], results: List[Dict[str, Any]]):
    if isinstance(attr, str):
        attr = [attr]

    names = lmap(lambda x: tuple(x[at] for at in attr), results)
    # Unlike set, Counter preserves insertion order.
    return list(collections.Counter(names))


def groupby(attr: Union[str, List[str]], results: List[Dict[str, Any]]):
    if isinstance(attr, str):
        attr = [attr]

    unique = get_unique(attr, results)

    return partition_n(
        len(unique), lambda x: unique.index(tuple(x[at] for at in attr)), results
    )


def log_to_console(results: List[Dict[str, str]], padding: int = 1):
    header_widths = lmap(len, results[0].keys())

    data_widths = zip(header_widths, *(lmap(len, d.values()) for d in results))

    column_widths: List[int] = lmap(max, data_widths)

    for i, res in enumerate(results):
        if i == 0:
            print(make_line(res.keys(), column_widths, padding=padding))
            print(make_separator(column_widths, padding=padding))

        print(make_line(res.values(), column_widths, padding=padding))
        # TODO: Print summary about improvements etc.


def reduce(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    reduced: Dict[str, Any] = {}

    # accumulate same name benchmarks into lists
    result = collections.defaultdict(list)
    for bm in results:
        for k, v in bm.items():
            result[k].append(v)

    for k, v in result.items():
        # all elements share one type due to the same schema
        if isinstance(v[0], float):
            mu = mean(v)
            sigma = pstdev(v, mu)
            # TODO: Allow other forms of reduction
            reduced[k] = (mu, sigma)
        else:
            reduced[k] = v[0]

    return reduced


def rescale(time_value: Tuple[float, float], current_unit: str, target_unit: str):
    if current_unit != target_unit:
        assert current_unit in unit_table, f"unknown time unit {current_unit!r}"
        assert target_unit in unit_table, f"unknown target time unit {target_unit!r}"

        target: float = unit_table[target_unit]
        current: float = unit_table[current_unit]

        scaled_time = tmap(lambda x: x * current / target, time_value)
    else:
        scaled_time = time_value

    return scaled_time


def sort_benchmark(bm: Dict[str, Any]) -> Dict[str, Any]:
    name_info, exec_info = split_list(PRIVILEGED_COLUMNS, 2)
    cols = name_info + lfilter(lambda x: "time" in x, bm.keys()) + exec_info

    reported_cols = sorted(
        [k for k in bm.keys() if k in cols], key=lambda x: cols.index(x)
    )

    return {k: bm[k] for k in reported_cols}


def transform_key(key: str) -> str:
    if key == "name":
        return ("benchmark " + key).title()

    # spaces, title case (capitalize each word)
    key = key.replace("_", " ").title()

    cap_list = ["Cpu", "Gpu"]
    for i, cap in enumerate(cap_list):
        if cap in key:
            key = key.replace(cap, cap.upper())

    return key
