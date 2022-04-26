import copy
import json
import sys
import time
import timeit
from typing import List, Any, Dict, Optional
from contextlib import redirect_stdout

import pybm.runners.util as runner_util
from pybm.runners.base import BaseRunner
from pybm.status_codes import SUCCESS
from pybm.util.common import dfilter
from pybm.util.functions import is_valid_timeit_target


class TimeitRunner(BaseRunner):
    """
    A benchmark runner class interface to dispatch benchmark runs in pybm
    using Python's builtin `timeit` module.
    """

    @staticmethod
    def make_context(benchmark_context: List[str]):
        # construct and fill context dictionary object
        context_dict: Dict[str, str] = {}

        # validate context first before JSON construction
        runner_util.validate_context(benchmark_context, parsed=True)

        for ctx in benchmark_context:
            name, value = ctx.split("=")
            context_dict[name] = value

        return context_dict

    def run_benchmark(
        self,
        argv: List[str] = None,
        module_context: Optional[Dict[str, Any]] = None,
    ) -> int:

        assert module_context is not None, "Module context is missing."

        argv = argv or sys.argv
        executable, *flags = argv

        flags += self.get_current_context()
        flags += [f"{self.prefix}_context=executable={executable}"]

        args = self.parse_flags(flags=flags)

        json_obj: Dict[str, Any] = {}

        module_targets = runner_util.filter_targets(
            module_context=module_context, regex_filter=args.benchmark_filter
        )

        # valid timeit target <=> is function + takes no args
        module_targets = dfilter(is_valid_timeit_target, module_targets)

        repeat: int = args.benchmark_repetitions

        benchmark_context: List[str] = args.benchmark_context or []

        # construct and fill context dictionary, add to JSON payload
        json_obj["context"] = self.make_context(benchmark_context)

        with redirect_stdout(None):
            # TODO: Implement random interleaving option with permutations
            benchmarks = []

            for name in module_targets.keys():
                benchmark_obj: Dict[str, Any] = {
                    "name": name,
                    "repetitions": repeat,
                    "repetition_index": 0,
                    "time_unit": "s",
                    "iterations": 0,
                }

                # explicit list comprehension to get unique object IDs
                objs = [copy.copy(benchmark_obj) for _ in range(repeat)]

                # Source for import:
                # https://docs.python.org/3/library/timeit.html#examples
                t_wall = timeit.Timer(
                    stmt=f"{name}()",
                    setup=f"from __main__ import {name}",
                    timer=time.process_time,
                )

                # Explanation of wall vs. CPU time in python's 'time':
                # https://stackoverflow.com/questions/25785243/understanding-time-perf-counter-and-time-process-time
                t_cpu = timeit.Timer(
                    stmt=f"{name}()",
                    setup=f"from __main__ import {name}",
                    timer=time.perf_counter,
                )

                try:
                    n_wall, _ = t_wall.autorange(None)
                    n_cpu, _ = t_cpu.autorange(None)

                    wall_times = t_wall.repeat(repeat=repeat, number=n_wall)
                    cpu_times = t_cpu.repeat(repeat=repeat, number=n_cpu)

                    for i, bm in enumerate(objs):
                        bm["real_time"] = wall_times[i] / n_wall
                        bm["cpu_time"] = cpu_times[i] / n_cpu
                        bm["repetition_index"] = i
                        bm["iterations"] = n_wall

                    benchmarks += objs

                except Exception as e:
                    # conform to GBM spec
                    # return single result, set timings to zero, add error message
                    return_obj = objs[0]
                    return_obj["real_time"] = return_obj["cpu_time"] = 0.0
                    return_obj["error_occurred"] = True
                    return_obj["error_message"] = str(e)

                    benchmarks += [return_obj]

            json_obj["benchmarks"] = benchmarks

        # write to stdout, to be read from the subprocess dispatched in `pybm run`.
        sys.stdout.write(json.dumps(json_obj))

        return SUCCESS
