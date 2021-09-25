from typing import List, Union, Optional, Sequence
from pathlib import Path

from pybm.config import PybmConfig
from pybm.runners.runner import BenchmarkRunner, ContextProvider
from pybm.specs import BenchmarkEnvironment


class GoogleBenchmarkRunner(BenchmarkRunner):
    """
    A benchmark runner class interface designed to dispatch benchmarking
    runs in pybm using Google Benchmark.
    """

    def __init__(self, config: PybmConfig):
        super().__init__(config=config)
        self.num_repetitions: int = config.get_value(
            "runner.GoogleBenchmarkNumRepetitions")
        self.with_interleaving: bool = config.get_value(
            "runner.GoogleBenchmarkWithRandomInterleaving")
        self.aggregates_only: bool = config.get_value(
            "runner.GoogleBenchmarkSaveAggregatesOnly"
        )

    def create_flags(
            self,
            out_file: Union[str, Path],
            benchmark_filter: Optional[str] = None,
            context_providers: Optional[Sequence[ContextProvider]] = None,
    ) -> List[str]:
        # JSON is the only supported file format in GBM
        flags = [f"--benchmark_out={out_file}",
                 "--benchmark_out_format=json"]
        if benchmark_filter is not None:
            flags.append(f"--benchmark_filter={benchmark_filter}")
        if self.num_repetitions > 0:
            flags.append(f"--benchmark_repetitions={self.num_repetitions}")
        if self.with_interleaving:
            flags.append("--benchmark_enable_random_interleaving=true")
        # Add benchmark context information like shown in
        # https://github.com/google/benchmark/blob/main/docs/user_guide.md#extra-context
        if context_providers is not None:
            for context_provider in context_providers:
                name, value = context_provider()
                flags.append(f"--benchmark_context={name}={value}")
        return flags

    def run_benchmarks(
            self,
            benchmarks: Sequence[str],
            environment: BenchmarkEnvironment,
            benchmark_filter: str = None,
            context_providers: Optional[Sequence[ContextProvider]] = None):
        self.check_required_packages(environment=environment)

        # stupid name, only used for printing below
        n = len(benchmarks)
        for i, target in enumerate(benchmarks):
            ref, _ = environment.workspace.get_ref_and_type()
            out_dir = Path(self.output_dir) / ref
            out_dir.mkdir(parents=True, exist_ok=True)
            out_name = Path(target).stem + "_results.json"
            command = [environment.venv.executable, target]
            command += self.create_flags(
                out_file=out_dir / out_name,
                benchmark_filter=benchmark_filter,
                context_providers=context_providers
            )
            print(f"Running benchmark {target}.....[{i + 1}/{n}]")
            self.run_subprocess(command=command, print_status=True)
