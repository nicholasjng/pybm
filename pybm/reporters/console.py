import collections
import json
import re
from functools import partial
from pathlib import Path
from typing import Union, Optional, Any, Dict, List, Callable

from pybm import PybmConfig
from pybm.exceptions import PybmError
from pybm.reporters.base import BaseReporter
from pybm.reporters.util import (
    rescale,
    get_unique_names,
    aggregate,
    log_to_console,
    format_time,
)
from pybm.util.common import (
    flatten,
    lfilter,
    lfilter_regex,
    dfilter_regex,
    partition_n,
    lmap,
    dmap,
)
from pybm.util.path import list_contents

PRIVILEGED_CONTEXT = ["executable", "ref"]
PRIVILEGED_INT_VALUED_COLUMNS = ["threads", "repetitions", "iterations"]


def process_dict(bm: Dict[str, Any], context: Dict[str, str], target_time_unit: str):
    """Process benchmark dict with its associated context. Order matters on
    construction - name and ref should come first, then timings,
    then iteration counts, then user context, then metrics."""
    # TODO: Assert these two exist
    python_file = Path(context["executable"])
    ref = context["ref"]

    # manual formatting, POSIX style
    target_path = python_file.parent.name + "/" + python_file.name

    formatted = {
        "Benchmark Name": target_path + ":" + bm.pop("name"),
        "Reference": ref,
        "Iterations": bm.pop("iterations"),
        "Repetitions": bm.pop("repetitions"),
    }

    time_unit: str = bm.pop("time_unit")
    time_values: Dict[str, float] = dfilter_regex(".*time", bm)

    for k in list(time_values.keys()):
        bm.pop(k)

    rescale_fn = partial(rescale, current_unit=time_unit, target_unit=target_time_unit)

    processed_times: Dict[str, float] = dmap(rescale_fn, time_values)

    formatted.update(processed_times)

    # merge in the remaining benchmark context
    for k, v in context.items():
        if k not in PRIVILEGED_CONTEXT:
            formatted[k] = v

    # only thing left should be the user counters
    # TODO: Think about how to merge in user counters while keeping away excess data
    # formatted.update(bm)

    return formatted


def process_result(benchmark_obj: Dict[str, Any], target_time_unit: str):
    # TODO: More extensive schema validation
    keys = ["context", "benchmarks"]
    if not all(key in benchmark_obj for key in keys):
        raise PybmError(
            f"Malformed JSON result detected. Result {benchmark_obj} missing "
            f"one or more of the expected keys {', '.join(keys)}."
        )

    benchmark_list = benchmark_obj["benchmarks"]
    # descriptive statistics on times and user counters
    aggregated_list = aggregate_results(benchmark_list)

    context = benchmark_obj["context"]

    process_fn = partial(
        process_dict, context=context, target_time_unit=target_time_unit
    )

    return lmap(process_fn, aggregated_list)


def filter_result(
    res: Dict[str, Any], context_filter: Optional[str], benchmark_filter: Optional[str]
) -> Dict[str, Any]:
    filtered_ctx, context = {}, res["context"]

    if context_filter is not None:
        # only display context values matching the filter regex
        filtered_ctx = dfilter_regex(context_filter, context)

    # add protected context values back, if not already present
    for val in PRIVILEGED_CONTEXT:
        if val in context:
            filtered_ctx[val] = context[val]

        res["context"] = filtered_ctx

    if benchmark_filter is not None:
        pattern = re.compile(benchmark_filter)
        res["benchmarks"] = lfilter(
            lambda bm: pattern.search(bm["name"]) is not None, res["benchmarks"]
        )

    return res


def compare_results(results: List[Dict[str, Any]], refs: List[str]):
    """Compare results between different refs. Assumes that the results and
    ref lists are sorted in the same order."""
    anchor_result = results[0]
    anchor_ref = refs[0]
    real_key = next(k for k in anchor_result.keys() if k.startswith("Wall"))

    for res in results:
        # relative time difference and speedup wrt anchor ref
        speedup = anchor_result[real_key][0] / res[real_key][0]
        dtime = 1.0 / speedup - 1.0
        res[f"Δt_rel ({anchor_ref})"] = dtime
        res["Speedup"] = speedup
        # TODO: Pop user counters to push them to the back too
        res["Iterations"] = res.pop("Iterations")
        res["Repetitions"] = res.pop("Repetitions")

    missing = len(refs) - len(results)
    fillers = []

    if missing > 0:
        # a result is missing for a ref
        missing_refs = refs[missing:]
        filler = "N/A"

        for ref in missing_refs:
            # pad values according to the dict schema of the anchor ref
            dummy_dict = {
                k: v if isinstance(v, str) else filler for k, v in anchor_result.items()
            }
            dummy_dict["Reference"] = ref
            fillers.append(dummy_dict)

    return results + fillers


def aggregate_results(results: List[Dict[str, Any]]):
    names = get_unique_names(results)
    aggregated_results = []
    partitions = partition_n(len(names), lambda x: names.index(x["name"]), results)

    def group_partition(p: List[Dict[str, Any]]):
        def partition_fn(key: str, value: Any) -> bool:
            """Return whether a value should be reduced or not."""
            if isinstance(value, (int, float)):
                # Do not aggregate rotected integer attributes and indices
                if key in PRIVILEGED_INT_VALUED_COLUMNS or key.endswith("index"):
                    return False
                else:
                    return True
            return False

        values_to_aggregate, constants = collections.defaultdict(list), {}

        for bm in p:
            for k, v in bm.items():
                if partition_fn(k, v):
                    values_to_aggregate[k].append(v)
                else:
                    constants[k] = v

        return values_to_aggregate, constants

    for partition in partitions:
        # partition values into reducible values (time / counters) and constants
        to_aggregate, result = group_partition(partition)
        aggregated = aggregate(to_aggregate)
        result.update(aggregated)
        aggregated_results.append(result)

    return aggregated_results


class ConsoleReporter(BaseReporter):
    def __init__(self, config: PybmConfig):
        super(ConsoleReporter, self).__init__(config=config)
        self.padding = 1
        self.formatters: Dict[str, Callable] = {
            "time": partial(
                format_time,
                digits=self.significant_digits,
                time_unit=self.target_time_unit,
            ),
            "rel_time": lambda x: f"{x:+.2%}",
            "Speedup": lambda x: f"{x:.2f}x",
        }

    def additional_arguments(self):
        args = [
            {
                "flags": "--target-filter",
                "type": str,
                "default": None,
                "metavar": "<regex>",
                "help": "Regex filter to selectively filter benchmark target files. "
                "If specified, only benchmark files matching the given regex will be "
                "included in the report.",
            },
            {
                "flags": "--benchmark-filter",
                "type": str,
                "default": None,
                "metavar": "<regex>",
                "help": "Regex filter to selectively report benchmarks from the "
                "matched target files. If specified, only benchmarks matching the "
                "given regex will be included in the report.",
            },
            {
                "flags": "--context-filter",
                "type": str,
                "default": None,
                "metavar": "<regex>",
                "help": "Regex filter for additional context to report from the "
                "benchmarks. If specified, context values matching the given "
                "regex will be included in the report.",
            },
        ]
        return args

    def compare(
        self,
        *refs: str,
        results: List[Union[str, Path]],
        report_absolutes: bool = False,
        target_filter: Optional[str] = None,
        benchmark_filter: Optional[str] = None,
        context_filter: Optional[str] = None,
    ):
        benchmarks_raw = []

        for ref in refs:
            for result in results:
                benchmarks_raw += self.load(
                    ref=ref, result=result, target_filter=target_filter
                )

        filter_fn = partial(
            filter_result,
            context_filter=context_filter,
            benchmark_filter=benchmark_filter,
        )

        process_fn = partial(process_result, target_time_unit=self.target_time_unit)

        compare_fn = partial(compare_results, refs=refs)

        filtered_results = lmap(filter_fn, benchmarks_raw)

        processed_results = flatten(lmap(process_fn, filtered_results))

        unique_names = get_unique_names(processed_results)

        # group all results by benchmark name
        grouped_results = partition_n(
            len(unique_names),
            lambda x: unique_names.index(x["Benchmark Name"]),
            processed_results,
        )

        if report_absolutes:
            compared_results = flatten(lmap(lambda x: x, grouped_results))
        else:
            compared_results = flatten(lmap(compare_fn, grouped_results))

        formatted_results = lmap(self.transform_result, compared_results)

        log_to_console(formatted_results, padding=self.padding)

    def load(
        self, ref: str, result: Union[str, Path], target_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        path = Path(self.result_dir) / result / ref

        if not path.exists() or not path.is_dir():
            raise PybmError(
                f"Given path {str(path)!r} does not exist or is not a directory."
            )

        json_files = list_contents(path=path, file_suffix=".json")

        if target_filter is not None:
            json_files = lfilter_regex(target_filter, json_files)

        results = []

        for result_file in json_files:
            with open(result_file, "r") as file:
                benchmark_obj = json.load(file)

            results.append(benchmark_obj)

        return results

    def transform_result(self, bm: Dict[str, Any]) -> Dict[str, str]:
        """Finalize column header names, cast all values to string and
        optionally format them, too (e.g. floating point numbers)."""
        transformed = {}

        for key, value in bm.items():
            if key.endswith(f"({self.target_time_unit})"):
                value_type = "time"
            elif key.startswith("Δt"):
                value_type = "rel_time"
            else:
                value_type = key

            transformed[key] = self.formatters.get(value_type, str)(value)

        return transformed
