import sys

import google_benchmark as gbm
from absl import app
from typing import List, Union, Optional
from pathlib import Path

from pybm.config import PybmConfig
from pybm.runners.runner import BenchmarkRunner
from pybm.specs import BenchmarkEnvironment
from pybm.util.common import lfilter


def flags_parser(argv: List[str]):
    argv = gbm.initialize(argv)
    return app.parse_flags_with_usage(argv)


class GoogleBenchmarkRunner(BenchmarkRunner):
    """
    A benchmark runner class interface designed to dispatch benchmark runs
    in pybm using Google Benchmark's Python bindings.
    """

    def __init__(self, config: PybmConfig):
        super().__init__(config=config)
        self.required_packages = ["google-benchmark"]
        self.with_interleaving: bool = config.get_value(
            "runner.GoogleBenchmarkWithRandomInterleaving")
        self.aggregates_only: bool = config.get_value(
            "runner.GoogleBenchmarkSaveAggregatesOnly")

    def create_flags(
            self,
            result_file: Union[str, Path],
            num_repetitions: int = 1,
            benchmark_filter: Optional[str] = None,
            benchmark_context: Optional[List[str]] = None) -> List[str]:
        flags = super(GoogleBenchmarkRunner, self).create_flags(
            result_file=result_file,
            num_repetitions=num_repetitions,
            benchmark_filter=benchmark_filter,
            benchmark_context=benchmark_context
        )
        if self.with_interleaving:
            flags.append("--benchmark_enable_random_interleaving=true")
        if self.aggregates_only:
            flags.append("--benchmark_report_aggregates_only")
        return flags

    def dispatch(
            self,
            benchmarks: List[str],
            environment: BenchmarkEnvironment,
            repetitions: int = 1,
            benchmark_filter: Optional[str] = None,
            benchmark_context: Optional[List[str]] = None):
        self.check_required_packages(environment=environment)
        result_dir = self.create_result_dir(environment=environment)

        # stupid name, only used for printing below
        n = len(benchmarks)
        for i, benchmark in enumerate(benchmarks):
            print(f"Running benchmark {benchmark}.....[{i + 1}/{n}]")
            python = environment.get_value("python.executable")
            worktree_root = environment.get_value("worktree.root")
            result_name = Path(benchmark).stem + "_results.json"
            command = [python, benchmark]
            command += self.create_flags(
                result_file=result_dir / result_name,
                num_repetitions=repetitions,
                benchmark_filter=benchmark_filter,
                benchmark_context=benchmark_context,
            )
            self.run_subprocess(command=command, cwd=worktree_root)

    def run_benchmark(self, args: List[str] = None):
        argv = args or sys.argv
        # inject environment-specific context into args
        argv += self.get_current_context()
        context = lfilter(lambda x: x.startswith("--benchmark_context"), argv)
        self.validate_context(context)

        argv = gbm.initialize(argv)
        return app.run(gbm.run_benchmarks, argv=argv,
                       flags_parser=flags_parser)
