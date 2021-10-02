import sys
from typing import List, Optional, Dict, Any

import google_benchmark as gbm
from absl import app

import pybm.runners.util as runner_util
from pybm.config import PybmConfig
from pybm.runners.runner import BenchmarkRunner
from pybm.util.common import lfilter


def flags_parser(argv: List[str]):
    argv = gbm.initialize(argv)
    return app.parse_flags_with_usage(argv)


def run_benchmarks(argv: List[str] = None):
    return gbm.run_benchmarks()


class GoogleBenchmarkRunner(BenchmarkRunner):
    """
    A benchmark runner class interface designed to dispatch benchmark runs
    in pybm using Google Benchmark's Python bindings.
    """

    def __init__(self, config: PybmConfig):
        super().__init__(config=config)
        self.required_packages = ["google-benchmark==0.2.0"]
        self.with_interleaving: bool = config.get_value(
            "runner.GoogleBenchmarkWithRandomInterleaving")
        self.aggregates_only: bool = config.get_value(
            "runner.GoogleBenchmarkSaveAggregatesOnly")

    def create_flags(
            self,
            num_repetitions: int = 1,
            benchmark_filter: Optional[str] = None,
            benchmark_context: Optional[List[str]] = None) -> List[str]:
        flags = super(GoogleBenchmarkRunner, self).create_flags(
            num_repetitions=num_repetitions,
            benchmark_filter=benchmark_filter,
            benchmark_context=benchmark_context
        )
        # JSON is the only supported output file format in GBM
        flags += [f"{self.prefix}_format=json"]
        if self.with_interleaving:
            flags.append("--benchmark_enable_random_interleaving=true")
        if self.aggregates_only:
            flags.append("--benchmark_report_aggregates_only")
        return flags

    def run_benchmark(self,
                      argv: List[str] = None,
                      context: Dict[str, Any] = None) -> int:
        # TODO: See if this works
        assert context is not None, "need to specify a module context"
        argv = argv or sys.argv
        # inject environment-specific context into args
        argv += self.get_current_context()
        runtime_context = lfilter(lambda x: x.startswith(
            "--benchmark_context"), argv)
        runner_util.validate_context(runtime_context, parsed=True)

        return app.run(run_benchmarks, argv=argv, flags_parser=flags_parser)
