import json
import re
from functools import partial
from pathlib import Path
from typing import Union, Optional, Any, Dict, List

from pybm import PybmConfig
from pybm.exceptions import PybmError
from pybm.reporters import BenchmarkReporter
from pybm.util.common import flatten, lfilter, lfilter_regex, lmap, dvmap, \
    dfilter_regex, partition_n
from pybm.util.path import list_contents
from pybm.util.print import make_line, make_separator

# timeit logs in seconds, GBM in nanoseconds
unit_table = {"s": 1., "sec": 1., "ms": 1e-3, "msec": 1e-3,
              "us": 1e-6, "usec": 1e-6, "ns": 1e-9, "nsec": 1e-9}


def get_column_widths(data: List[Dict[str, str]]):
    header_widths = lmap(len, data[0].keys())
    data_lengths = zip(header_widths, *(lmap(len, d.values()) for d in data))
    return lmap(max, data_lengths)


def rescale(time_value: float, current_unit: str, target_unit: str):
    if current_unit != target_unit:
        assert current_unit in unit_table, \
            f"unknown time unit {current_unit!r}"
        target = unit_table[target_unit]
        current = unit_table[current_unit]
        time_value *= current / target
    # formatting nsecs as ints is nicer
    if target_unit in ["ns", "nsec"]:
        return int(time_value)
    else:
        return time_value


def process_dict(bm: Dict[str, Any],
                 context: Dict[str, str],
                 target_time_unit: str):
    """Process benchmark dict with its associated context. Order matters on
    construction - name and ref should come first, then timings,
    then iteration counts, then user context, then metrics."""
    # TODO: Assert these two exist
    python_file = Path(context.pop("executable"))
    ref = context.pop("ref")
    # manual formatting, POSIX style
    target_path = python_file.parent.name + "/" + python_file.name
    formatted = {"name": target_path + ":" + bm["name"],
                 "ref": ref}

    time_unit: str = bm.pop("time_unit")
    time_values: Dict[str, float] = dfilter_regex(".*_time", bm)
    rescale_fn = partial(rescale,
                         current_unit=time_unit,
                         target_unit=target_time_unit)
    processed_times: Dict[str, float] = dvmap(rescale_fn, time_values)

    formatted.update(processed_times)
    formatted.update({"iterations": bm["iterations"]})
    # merge in the benchmark context entirely
    # TODO: Assert no key occurs twice (i.e. gets overwritten)
    formatted.update(context)
    # TODO: Grab user counters and inject them raw
    return formatted


def process_result(benchmark_obj: Dict[str, Any],
                   target_time_unit: str):
    # TODO: More extensive schema validation
    keys = ["context", "benchmarks"]
    if not all(key in benchmark_obj for key in keys):
        raise PybmError(f"Malformed JSON result detected. "
                        f"Result {benchmark_obj} missing at least one "
                        f"of the expected keys {', '.join(keys)}.")
    benchmark_list = benchmark_obj["benchmarks"]
    context = benchmark_obj["context"]
    do_format = partial(process_dict,
                        context=context,
                        target_time_unit=target_time_unit)
    formatted_list = lmap(do_format, benchmark_list)
    return formatted_list


def filter_result(res: Dict[str, Any],
                  context_filter: str,
                  benchmark_filter: str) -> Dict[str, Any]:
    protected_context = ["executable", "ref"]
    if context_filter is not None:
        filtered = dfilter_regex(context_filter, res["context"])
        # add protected context values back
        for val in protected_context:
            filtered[val] = res[val]
        res["context"] = filtered
    if benchmark_filter is not None:
        pattern = re.compile(benchmark_filter)
        res["benchmarks"] = lfilter(
            lambda bm: pattern.search(bm["name"]) is not None,
            res["benchmarks"])
    return res


def compare_results(results: List[Dict[str, Any]],
                    refs: List[str]):
    """Compare results between different refs. Assumes that the results and
    ref lists are sorted in the same order."""
    anchor_result, *others = results
    anchor_ref, *other_refs = refs
    dtime_key = f"dtime_rel ({anchor_ref})"
    for res in others:
        # relative time difference and speedup wrt anchor ref
        speedup = (anchor_result["real_time"] / res["real_time"])
        dtime = 1. / speedup - 1.
        res[dtime_key] = dtime
        res["speedup"] = speedup

    anchor_result[dtime_key] = 0.0
    anchor_result["speedup"] = 1.0
    # TODO: Pop iteration number here to wrap it around and
    #  have it appear last in the printed table

    # TODO: Warn here about a missing result
    # case when a result is missing for a ref
    # pad values according to the dict schema of the anchor ref
    missing = len(refs) - len(results)
    fillers = []
    if missing > 0:
        missing_refs = refs[missing:]
        filler = "N/A"
        for ref in missing_refs:
            dummy_dict = {k: v if isinstance(v, str) else filler for k, v in
                          anchor_result.items()}
            dummy_dict["ref"] = ref
            fillers.append(dummy_dict)
    return results + fillers


class JSONReporter(BenchmarkReporter):
    def __init__(self, config: PybmConfig):
        super(JSONReporter, self).__init__(config=config)
        self.padding = 1
        self.formatters = {
            int: str,
            str: lambda x: x,
            float: lambda x: f"{x:.{self.significant_digits}f}"}

    def compare(self,
                *refs: str,
                result: Union[str, Path],
                target_filter: Optional[str] = None,
                benchmark_filter: Optional[str] = None,
                context_filter: Optional[str] = None
                ):
        benchmarks_raw = []
        for ref in refs:
            benchmarks_raw += self.load(ref=ref, result=result,
                                        target_filter=target_filter)
        filter_fn = partial(filter_result,
                            context_filter=context_filter,
                            benchmark_filter=benchmark_filter)
        process_fn = partial(process_result,
                             target_time_unit=self.target_time_unit)
        compare_fn = partial(compare_results, refs=refs)

        filtered_results = lmap(filter_fn, benchmarks_raw)
        processed_results = flatten(lmap(process_fn, filtered_results))
        grouped_results = partition_n(len(refs),
                                      lambda x: refs.index(x["ref"]),
                                      processed_results)
        compared_results = flatten(lmap(compare_fn, grouped_results))
        formatted_results = lmap(self.transform_result, compared_results)
        self.log_to_console(formatted_results)

    def report(self,
               ref: str,
               result: Union[str, Path],
               target_filter: Optional[str] = None,
               benchmark_filter: Optional[str] = None,
               context_filter: Optional[str] = None):
        benchmark_results = self.load(ref=ref, result=result,
                                      target_filter=target_filter)
        filter_fn = partial(filter_result,
                            context_filter=context_filter,
                            benchmark_filter=benchmark_filter)
        process_fn = partial(process_result,
                             target_time_unit=self.target_time_unit)
        format_fn = self.transform_result

        filtered_results = lmap(filter_fn, benchmark_results)
        processed_results = flatten(lmap(process_fn, filtered_results))
        print(processed_results)
        formatted_results = lmap(format_fn, processed_results)
        print(formatted_results)
        self.log_to_console(formatted_results)

    def load(self, ref: str, result: Union[str, Path],
             target_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        path = Path(self.result_dir) / result / ref
        if not path.exists() or not path.is_dir():
            raise PybmError(f"Given result path {result} does not exist, or "
                            f"is not a directory.")
        json_files = list_contents(path=path,
                                   file_suffix=".json",
                                   names_only=False)
        if target_filter is not None:
            json_files = lfilter_regex(target_filter, json_files)
        results = []
        for result_file in json_files:
            with open(result_file, "r") as file:
                benchmark_obj = json.load(file)
            results.append(benchmark_obj)
        return results

    def log_to_console(self, results: List[Dict[str, str]]):
        column_widths = get_column_widths(results)
        padding = self.padding
        for i, res in enumerate(results):
            if i == 0:
                print(make_line(res.keys(), column_widths, padding=padding))
                print(make_separator(column_widths, padding=padding))
            print(make_line(res.values(), column_widths, padding=padding))

    def transform_result(self, bm: Dict[str, Any]) -> Dict[str, str]:
        """Finalize column header names, cast all values to string and
        optionally format them, too (e.g. floating point numbers)."""
        transformed = {}
        for key, value in bm.items():
            if key.endswith("_time"):
                key = key.split("_")[0]
                key = key.upper() if key in ["cpu", "gpu"] else "Wall"
                key += f" Time ({self.target_time_unit})"
            elif key == "name":
                key = "Benchmark Name"
            elif key.startswith("dtime"):
                # TODO: Format value as percentage
                # relative time difference key
                key = key.replace("dtime", "Δt")
            else:
                key = key.capitalize()
            value_type = type(value)
            value = self.formatters[value_type](value)

            transformed[key] = value
        return transformed
