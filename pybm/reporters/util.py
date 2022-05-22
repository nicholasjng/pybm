import collections
import typing
from typing import Any, Callable, Dict, Iterable, List, Union

from pybm.util.common import lmap, partition_n, safe_index
from pybm.util.formatting import make_line, make_separator

# metric time units
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

PRIVILEGED_COLUMNS = [
    "benchmark_name",
    "reference",
    "real_time",
    "delta_real_time",
    "cpu_time",
    "delta_cpu_time",
    "gpu_time",
    "delta_gpu_time",
    "speedup",
    "iterations",
    "threads",
    "repetitions",
    "error_occurred",
    "error_message",
]

Schema = Dict[str, type]


def get_unique(attr: Union[List[str], Callable], results: Iterable[Dict[str, Any]]):
    if isinstance(attr, list):
        names = map(lambda x: tuple(x[at] for at in attr), results)  # type: ignore
    else:
        names = map(attr, results)

    # Unlike set, Counter preserves insertion order.
    return list(collections.Counter(names))


@typing.overload
def groupby(attr: str, results: Iterable[Dict[str, Any]]):
    ...


@typing.overload
def groupby(attr: List[str], results: Iterable[Dict[str, Any]]):
    ...


@typing.overload
def groupby(attr: Callable, results: Iterable[Dict[str, Any]]):
    ...


def groupby(attr, results: Iterable[Dict[str, Any]]):
    if isinstance(attr, str):
        attr = [attr]

    unique = get_unique(attr, results)

    if isinstance(attr, list):
        return partition_n(
            len(unique), lambda x: unique.index(tuple(x[at] for at in attr)), results
        )
    else:
        return partition_n(len(unique), lambda x: unique.index(attr(x)), results)


def infer_schema(benchmarks: List[Dict[str, Any]]) -> Schema:
    """
    Infer a schema from the data based on the data in the benchmark objects.

    This does NOT assume that every datapoint contains exactly the same columns;
    rather, the entries in the resulting schema represent the union of all columns
    from all considered benchmark objects.

    If necessary, the results can then be padded in a later processing step.
    """
    schema: Schema = {}

    # data types in strength, high to low.
    # TODO: Support more types (datetime, etc.)
    _type_lattice: Dict[type, int] = {
        bool: 4,
        int: 3,
        float: 2,  # every int can be a float
        str: 1,  # every number can be interpreted as a string
    }

    for bm in benchmarks:
        # JSON handles value parsing, so no casts necessary
        for k, v in bm.items():
            value_type = type(v)
            # TODO: This disallows lists/dicts, support them separately
            assert value_type in _type_lattice, "unknown data type"

            if k in schema:
                if _type_lattice[value_type] >= _type_lattice[schema[k]]:
                    # k in schema, but data type matches
                    continue
                else:
                    # demote column to weaker type
                    schema[k] = value_type
            else:
                schema[k] = value_type

    return schema


def log_to_console(results: List[Dict[str, str]], schema: Schema, padding: int = 1):
    header_widths = lmap(len, results[0].keys())

    data_widths = zip(header_widths, *(lmap(len, d.values()) for d in results))

    column_widths: List[int] = lmap(max, data_widths)

    for i, res in enumerate(results):
        if i == 0:
            print(make_line(res.keys(), column_widths, padding=padding))
            print(make_separator(column_widths, padding=padding))

        print(make_line(res.values(), column_widths, padding=padding))


def rescale(value: float, current_unit: str, target_unit: str):
    if current_unit != target_unit:
        assert current_unit in unit_table, f"unknown time unit {current_unit!r}"
        assert target_unit in unit_table, f"unknown target time unit {target_unit!r}"

        target: float = unit_table[target_unit]
        current: float = unit_table[current_unit]

        return value * current / target
    else:
        return value


def sort_benchmark(bm: Dict[str, Any]) -> Dict[str, Any]:
    # heuristic: either in privileged columns, or a float (= user counter)
    reported_cols = sorted(
        [k for k, v in bm.items() if k in PRIVILEGED_COLUMNS or isinstance(v, float)],
        key=lambda x: safe_index(PRIVILEGED_COLUMNS, x),
    )

    return {k: bm[k] for k in reported_cols}


def transform_key(key: str) -> str:
    # spaces, title case (capitalize each word)
    key = key.replace("delta", "Δ")
    key = key.replace("_", " ").title()

    cap_list = ["Cpu", "Gpu"]
    for i, cap in enumerate(cap_list):
        if cap in key:
            key = key.replace(cap, cap.upper())

    return key
