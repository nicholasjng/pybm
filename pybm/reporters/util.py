from statistics import mean, pstdev
from typing import Tuple, List, Dict, Any, Union

from pybm.util.common import tmap, lmap
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


def aggregate(bm: Dict[str, List[Union[int, float]]]) -> Dict[str, Union[int, float]]:
    res: Dict[str, Any] = {}

    for k, v in bm.items():
        # all elements share one type due to the same schema
        value_type: type = type(v[0])
        mu = mean(v)
        sigma = pstdev(v, mu)
        # type casting floors int values
        # TODO: Allow other forms of reduction
        res[k] = (value_type(mu), value_type(sigma))

    return res


def format_time(time: Tuple[float, float], time_unit: str, digits: int) -> str:
    tval, std = time

    if time_unit.startswith("ns"):
        # formatting nsecs as ints is nicer
        res = f"{int(tval)} ± {int(std)}"
    else:
        res = f"{tval:.{digits}f} ± {std:.{digits}f}"

    return res


def get_unique_names(results: List[Dict[str, Any]]):
    if "name" in results[0]:
        name_key = "name"
    elif "Benchmark Name" in results[0]:
        name_key = "Benchmark Name"
    else:
        raise AttributeError("Benchmark name could not be found.")

    names = lmap(lambda x: x[name_key], results)
    return list(set(names))


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


def rescale(
    key: str, time_value: Tuple[float, float], current_unit: str, target_unit: str
):
    ttype = key.split("_")[0]
    tkey = ttype.upper() if ttype in ["cpu", "gpu"] else "Wall"
    tkey += f" Time ({target_unit})"

    if current_unit != target_unit:
        assert current_unit in unit_table, f"unknown time unit {current_unit!r}"
        assert target_unit in unit_table, f"unknown target time unit {target_unit!r}"

        target: float = unit_table[target_unit]
        current: float = unit_table[current_unit]

        scaled_time = tmap(lambda x: x * current / target, time_value)
    else:
        scaled_time = time_value

    return tkey, scaled_time
