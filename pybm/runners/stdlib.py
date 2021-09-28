import functools
import json
import re
import timeit
from pathlib import Path
from typing import List, Optional, Any, Tuple, Dict

from pybm.config import PybmConfig
from pybm.runners.runner import BenchmarkRunner
from pybm.specs import BenchmarkEnvironment
from pybm.util.common import dfilter
from pybm.util.functions import is_valid_timeit_target


def is_module_member(obj_tuple: Tuple[str, Any], module_name: str):
    """Check membership of object in __main__ module to avoid benchmarking
    imports due to accidentally pattern matching them."""
    obj = obj_tuple[1]
    if not hasattr(obj, "__module__"):
        return False
    else:
        return obj.__module__ == module_name


class TimeitBenchmarkRunner(BenchmarkRunner):
    """
    A benchmark runner class interface designed to dispatch benchmarking
    runs in pybm using Google Benchmark.
    """

    def __init__(self, config: PybmConfig):
        super().__init__(config=config)

    def dispatch(
            self,
            benchmarks: List[str],
            environment: BenchmarkEnvironment,
            repetitions: int = 1,
            benchmark_filter: Optional[str] = None,
            benchmark_context: Optional[List[str]] = None):
        result_dir = self.create_result_dir(environment=environment)
        # stupid name, only used for printing below
        n = len(benchmarks)
        print(f"Found a total of {n} benchmark targets for "
              f"environment {environment.name!r}.")
        for i, benchmark in enumerate(benchmarks):
            print(f"Running benchmark {benchmark}.....[{i + 1}/{n}]")
            python = environment.get_value("python.executable")
            worktree_root = environment.get_value("worktree.root")
            result_name = Path(benchmark).stem + "_results.json"
            result_file = result_dir / result_name
            command = [python, benchmark]
            command += self.create_flags(
                result_file=result_file,
                num_repetitions=repetitions,
                benchmark_filter=benchmark_filter,
                benchmark_context=benchmark_context,
            )
            self.run_subprocess(command, cwd=worktree_root)

    def run_benchmark(self, args: List[str] = None):
        flag_parser = self.create_parser()
        options = flag_parser.parse_args(args)
        json_obj: Dict[str, Any] = {}
        out_path = options.benchmark_out

        # filter admissible targets as those from the __main__ module
        # of the subprocess (target .py file)
        is_main_member = functools.partial(is_module_member,
                                           module_name="__main__")
        module_targets = dfilter(is_main_member, globals())
        # valid timeit target <=> is function + takes no args
        module_targets = dfilter(is_valid_timeit_target, module_targets)
        benchmark_filter = options.benchmark_filter
        if benchmark_filter is not None:
            pattern = re.compile(options.benchmark_filter)
            module_targets = dfilter(
                lambda x: pattern.match(x[0]) is not None, module_targets)

        # construct and fill context dictionary object
        benchmark_context: List[str] = options.benchmark_context
        context_dict: Dict[str, str] = {}
        for ctx in benchmark_context:
            name, value = ctx.split("=")
            context_dict[name] = value
        # add to JSON object
        json_obj["context"] = context_dict

        num_reps = options.benchmark_repetitions
        benchmarks = []
        for name, func in module_targets.items():
            benchmark_obj: Dict[str, Any] = {"name": name}
            # Source: https://docs.python.org/3/library/timeit.html#examples
            t = timeit.Timer(stmt=f"{name}()", globals=globals())
            benchmark_obj["times"] = t.repeat(repeat=num_reps)
            benchmarks.append(benchmark_obj)

        json_obj["benchmarks"] = benchmarks
        with open(out_path, "w") as result_file:
            json.dump(json_obj, fp=result_file)
