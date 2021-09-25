from typing import List, Union, Optional, Sequence
import timeit
from pathlib import Path
import json

from pybm.config import PybmConfig
from pybm.runners.runner import BenchmarkRunner, ContextProvider
from pybm.specs import BenchmarkEnvironment


class StdlibBenchmarkRunner(BenchmarkRunner):
    """
    A benchmark runner class interface designed to dispatch benchmarking
    runs in pybm using Google Benchmark.
    """

    def __init__(self, config: PybmConfig):
        super().__init__(config=config)

    def run_benchmarks(
            self,
            benchmarks: Sequence[str],
            environment: BenchmarkEnvironment,
            benchmark_filter: Optional[str] = None,
            context_providers: Optional[Sequence[ContextProvider]] = None):
        # stupid name, only used for printing below
        n = len(benchmarks)
        for i, target in enumerate(benchmarks):
            ref, _ = environment.workspace.get_ref_and_type()
            out_dir = Path(self.output_dir) / ref
            out_dir.mkdir(parents=True, exist_ok=True)
            out_name = Path(target).stem + "_results.json"
            print(f"Running benchmark {target}.....[{i + 1}/{n}]")

