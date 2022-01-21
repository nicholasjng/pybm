import json
import sys
import time
import timeit
from typing import List, Any, Dict, Optional
from contextlib import redirect_stdout

import pybm.runners.util as runner_util
from pybm import PybmError
from pybm.config import PybmConfig
from pybm.runners.base import BaseRunner
from pybm.status_codes import SUCCESS
from pybm.util.common import dfilter
from pybm.util.functions import is_valid_timeit_target


class TimeitRunner(BaseRunner):
    """
    A benchmark runner class interface designed to dispatch benchmarking
    runs in pybm using Google Benchmark.
    """

    def __init__(self, config: PybmConfig):
        super().__init__(config=config)

    def additional_arguments(self):
        return []

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

        if module_context is None:
            raise PybmError(
                "Missing module context. Please specify a context for "
                "benchmark execution (the easiest way to do this is by "
                "passing the globals() object)."
            )

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
        # TODO: Log warning about thrown away targets

        repetitions: int = args.benchmark_repetitions

        benchmark_context: List[str] = args.benchmark_context or []

        # construct and fill context dictionary, add to JSON payload
        json_obj["context"] = self.make_context(benchmark_context)

        benchmark_objects = []

        # TODO: Enable stdout redirect to logfile
        with redirect_stdout(None):
            # TODO: Give option of aggregate-only reporting
            for i in range(repetitions):
                # TODO: Implement random interleaving option with permutations
                for name in module_targets.keys():
                    benchmark_obj: Dict[str, Any] = {
                        "name": name,
                        "repetitions": repetitions,
                        "repetition_index": i,
                    }
                    # Source for import:
                    # https://docs.python.org/3/library/timeit.html#examples
                    t_real = timeit.Timer(
                        stmt=f"{name}()",
                        setup=f"from __main__ import {name}",
                        timer=time.perf_counter,
                    )

                    # Explanation of real vs. CPU time in python's 'time':
                    # https://stackoverflow.com/questions/25785243/understanding-time-perf-counter-and-time-process-time
                    t_cpu = timeit.Timer(
                        stmt=f"{name}()",
                        setup=f"from __main__ import {name}",
                        timer=time.process_time,
                    )

                    for t, ttype in [(t_real, "real_time"), (t_cpu, "cpu_time")]:
                        number, _ = t.autorange(None)

                        # TODO: What if these are different?
                        benchmark_obj["iterations"] = number

                        # TODO: Give option to specify time unit
                        benchmark_obj["time_unit"] = "s"

                        # set repetitions to 1 here to be able to write the
                        # resulting data to JSON
                        benchmark_obj[ttype] = (
                            min(t.repeat(repeat=1, number=number)) / number
                        )

                    benchmark_objects.append(benchmark_obj)

            json_obj["benchmarks"] = benchmark_objects

        # write the JSON object to stdout, to be caught by the subprocess
        # started in the run command.
        sys.stdout.write(json.dumps(json_obj))

        return SUCCESS
