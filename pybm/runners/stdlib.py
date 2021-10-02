import argparse
import json
import sys
import time
import timeit
from typing import List, Any, Dict, Optional

import pybm.runners.util as runner_util
from pybm.config import PybmConfig
from pybm.runners.runner import BenchmarkRunner
from pybm.status_codes import SUCCESS
from pybm.util.common import dfilter
from pybm.util.functions import is_valid_timeit_target


class TimeitRunner(BenchmarkRunner):
    """
    A benchmark runner class interface designed to dispatch benchmarking
    runs in pybm using Google Benchmark.
    """

    def __init__(self, config: PybmConfig):
        super().__init__(config=config)

    def parse_flags(self, flags: List[str]):
        prefix = self.prefix
        parser = argparse.ArgumentParser(prog=self.__class__.__name__,
                                         add_help=False)
        parser.add_argument(f"{prefix}_filter",
                            type=str,
                            default=None)
        parser.add_argument(f"{prefix}_repetitions",
                            type=int)
        parser.add_argument(f"{prefix}_context",
                            action="append",
                            default=None)
        return parser.parse_args(flags)

    @staticmethod
    def make_context(benchmark_context: Optional[List[str]] = None):
        # construct and fill context dictionary object
        context_dict: Dict[str, str] = {}
        if benchmark_context is not None:
            # validate context first before JSON construction
            runner_util.validate_context(benchmark_context, parsed=True)
            for ctx in benchmark_context:
                name, value = ctx.split("=")
                context_dict[name] = value
        return context_dict

    def run_benchmark(self,
                      argv: List[str] = None,
                      context: Dict[str, Any] = None) -> int:
        assert context is not None, "need to specify a module context"
        argv = argv or sys.argv
        executable, *flags = argv
        flags += self.get_current_context()
        flags += [f"{self.prefix}_context=executable={executable}"]
        args = self.parse_flags(flags=flags)
        json_obj: Dict[str, Any] = {}

        module_targets = runner_util.filter_targets(
            module_context=context, regex_filter=args.benchmark_filter)
        # valid timeit target <=> is function + takes no args
        module_targets = dfilter(is_valid_timeit_target, module_targets)

        benchmark_context: Optional[List[str]] = args.benchmark_context
        # construct and fill context dictionary, add to JSON payload
        json_obj["context"] = self.make_context(benchmark_context)

        benchmark_objects = []
        for name in module_targets.keys():
            benchmark_obj: Dict[str, Any] = {"name": name}
            # Source: https://docs.python.org/3/library/timeit.html#examples
            t_real = timeit.Timer(stmt=f"{name}()",
                                  setup=f"from __main__ import {name}",
                                  timer=time.perf_counter)
            # Explanation real vs. CPU time:
            # https://stackoverflow.com/questions/25785243/understanding-time-perf-counter-and-time-process-time
            t_cpu = timeit.Timer(stmt=f"{name}()",
                                 setup=f"from __main__ import {name}",
                                 timer=time.process_time)
            for t, measured in [(t_real, "real_time"), (t_cpu, "cpu_time")]:
                number, _ = t.autorange(None)
                # TODO: What if these are different?
                benchmark_obj["iterations"] = number
                # TODO: Give option to specify time unit
                benchmark_obj["time_unit"] = "s"
                # TODO: Give option to log raw list instead of min
                benchmark_obj[measured] = min(t.repeat(
                    repeat=args.benchmark_repetitions, number=number)) / number

            benchmark_objects.append(benchmark_obj)

        json_obj["benchmarks"] = benchmark_objects
        # write the JSON object to stdout, to be caught by the subprocess
        # started in the run command.
        sys.stdout.write(json.dumps(json_obj))
        return SUCCESS
