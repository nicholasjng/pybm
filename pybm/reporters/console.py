import copy
from collections import defaultdict
from functools import partial
from statistics import mean, stdev
from typing import Any, Dict, List, Optional, Tuple

from pybm.io.json import JSONFileIO
from pybm.reporters.base import BaseReporter
from pybm.reporters.util import (
    groupby,
    infer_schema,
    log_to_console,
    rescale,
    sort_benchmark,
    transform_key,
)
from pybm.util.common import (
    dfilter_regex,
    dvmap,
    flatten,
    lmap,
    partition_n,
    safe_index,
)
from pybm.util.formatting import (
    format_benchmark,
    format_floating,
    format_ref,
    format_relative,
    format_speedup,
)
from pybm.util.path import get_subdirs


def compare(results: List[Dict[str, Any]], refs: Tuple[str, ...]):
    """Compare results between different refs with respect to an anchor ref. Assumes
    that the results are sorted in the same order."""
    results = sorted(results, key=lambda x: safe_index(refs, x["ref"]))

    anchor_result, anchor_ref = results[0], refs[0]

    # not enough results to compare, or result is missing for the anchor ref
    if len(results) <= 1 or anchor_result["ref"] != anchor_ref:
        return results

    for result in results:
        relative = {}
        for k, v in result.items():
            if isinstance(v, float):
                tkey = f"delta_{k}"
                # relative difference and speedup w.r.t. anchor ref
                speedup = anchor_result[k] / v
                relative[tkey] = 1.0 / speedup - 1.0
                if "time" in k or "coefficient" in k:
                    relative["speedup"] = speedup

        # add relative differences to the result
        result.update(relative)

    return results


def format(aggregates: List[Dict[str, Any]], time_unit: str, digits: int):
    mean_agg = stddev_agg = {}

    for agg in aggregates:
        split_name, agg_name = agg["name"].rsplit("_", maxsplit=1)
        if agg_name == "mean":
            mean_agg = agg
        elif agg_name == "stddev":
            stddev_agg = agg

    assert mean_agg, "missing mean aggregate result"

    sorted_bm = sort_benchmark(mean_agg)
    transformed = {}

    for key, value in sorted_bm.items():
        tkey = transform_key(key)

        if key.startswith("delta"):
            tvalue = format_relative(value, digits=digits)
        elif key == "speedup":
            tvalue = format_speedup(value, digits=digits)
        # general float columns that are not relative/speedup
        elif isinstance(value, float):
            tkey += f" ({time_unit})"
            std = stddev_agg.get(key, None)
            tvalue = format_floating(value, digits=digits, std=std, as_integers=False)
        elif key == "benchmark_name":
            tvalue = value.rsplit("_", maxsplit=1)[0]
        else:
            tvalue = str(value)

        transformed[tkey] = tvalue

    return transformed


def process(bm: Dict[str, Any], time_unit: str, shalength: int):
    """
    Process benchmark dict with its associated context. Order matters on
    construction - name and ref should come first, then timings, then iteration
    counts, then user context, then metrics.
    """
    bm["benchmark_name"] = format_benchmark(bm["name"], bm["executable"])
    bm["reference"] = format_ref(bm["ref"], bm["commit"], shalength=shalength)

    current_unit: Optional[str] = bm.pop("time_unit", None)

    if time_unit is not None:
        time_values: Dict[str, Any] = dfilter_regex(r"\w+_(time|coefficient)", bm)

        rescale_fn = partial(rescale, current_unit=current_unit, target_unit=time_unit)

        bm.update(dvmap(rescale_fn, time_values))

    return bm


def reduce(results: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], ...]:
    reduced: Dict[str, Any] = {}
    # for holding secondary metrics (standard deviation etc.)
    reduced_copy = copy.copy(reduced)

    # fast path for the scenarios:
    # 1) error during benchmark (results in single result object)
    # 2) result is already an aggregate (e.g. pre-calculated like in GBM)
    if len(results) == 1:
        return tuple(results)

    # accumulate same name benchmarks into lists
    result = defaultdict(list)
    for bm in results:
        for k, v in bm.items():
            result[k].append(v)

    for k, v in result.items():
        # all elements share one type due to the same schema
        first = v[0]
        if isinstance(first, (int, float)):
            # TODO: Allow other forms of reduction
            mu = mean(v)
            reduced[k] = mu
            reduced_copy[k] = stdev(v, mu)
        else:
            reduced[k] = first + "_mean" if k == "name" else first
            reduced_copy[k] = first + "_stddev" if k == "name" else first

    return reduced, reduced_copy


class JSONConsoleReporter(BaseReporter):
    def __init__(self):
        super(JSONConsoleReporter, self).__init__()

        # file IO for reading / writing JSON files
        self.io = JSONFileIO(result_dir=self.result_dir)  # type: ignore
        self.padding = 1

    def compare(
        self,
        *refs: str,
        absolute: bool = False,
        previous: int = 1,
        sort_by: str = None,
        time_unit: str = "ns",
        digits: int = 2,
        as_integers: bool = False,
        shalength: int = 8,
        target_filter: Optional[str] = None,
        benchmark_filter: Optional[str] = None,
        context_filter: Optional[str] = None,
    ):
        results = sorted(get_subdirs(self.result_dir), key=int)[: -previous - 1 : -1]

        benchmarks = []
        for result in results:
            benchmarks += self.read(
                *refs,
                result=result,
                target_filter=target_filter,
                benchmark_filter=benchmark_filter,
                context_filter=context_filter,
            )

        process_fn = partial(
            process,
            time_unit=self.target_time_unit,
            shalength=self.shalength,
        )

        benchmarks = lmap(process_fn, benchmarks)

        repetitions, aggregates = partition_n(
            2,
            lambda x: x.get("run_type", None) == "aggregate",
            benchmarks,
        )

        # aggregate results with the same name and commit
        # TODO: Add timestamp
        if not aggregates:
            aggregates = flatten(
                [
                    reduce(group)
                    for group in groupby(["family_index", "commit"], repetitions)
                ]
            )

        if not absolute:
            aggregates = flatten(
                [compare(group, refs=refs) for group in groupby(["name"], aggregates)]
            )

        schema = infer_schema(aggregates)

        formatted_results = [
            format(
                group, time_unit=self.target_time_unit, digits=self.significant_digits
            )
            for group in groupby("ref", aggregates)
        ]

        log_to_console(formatted_results, schema=schema, padding=self.padding)
        # TODO: Print summary about improvements, regressions etc.
