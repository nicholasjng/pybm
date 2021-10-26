from pathlib import Path
from typing import Optional, Tuple, Callable, List, Any, Dict

import pybm.runners.util as runner_util
from pybm import PybmConfig
from pybm.exceptions import PybmError
from pybm.specs import BenchmarkEnvironment
from pybm.util.common import lmap
from pybm.util.imports import convert_to_module
from pybm.util.subprocess import run_subprocess

# A context provider produces name and value of a contextual
# piece of information, e.g. processor architecture, cwd etc.
ContextProvider = Callable[[], Tuple[str, str]]


class BenchmarkRunner:
    """Base class for all pybm benchmark runners."""

    def __init__(self, config: PybmConfig):
        super().__init__()
        self.prefix = "--benchmark"

        # required packages for the runner
        self.required_packages: List[str] = []

        # result saving directory; create if non-existent
        self.result_dir: str = config.get_value("runner.resultDirectory")
        Path(self.result_dir).mkdir(parents=True, exist_ok=True)

        self.fail_fast: bool = config.get_value("runner.failFast")
        self.context_providers: List[ContextProvider] = \
            runner_util.load_context_providers(config.get_value(
                "runner.contextProviders"))

    def check_required_packages(self, environment: BenchmarkEnvironment):
        missing_pkgs = []
        installed = environment.get_value("python.packages")
        for pkg in self.required_packages:
            if pkg not in installed:
                missing_pkgs.append(pkg)
        if len(missing_pkgs) > 0:
            raise PybmError(f"Required packages {', '.join(missing_pkgs)} "
                            f"for runner {self.__class__.__name__} not "
                            f"installed in environment {environment.name!r}. "
                            f"To install them, run `pybm env install "
                            f"{environment.name} {' '.join(missing_pkgs)}`.")

    def create_flags(
            self,
            environment: BenchmarkEnvironment,
            num_repetitions: int = 5,
            benchmark_filter: Optional[str] = None,
            benchmark_context: Optional[List[str]] = None) -> List[str]:
        flags, prefix = [], self.prefix
        ref, _ = environment.worktree.get_ref_and_type(bare=True)

        if benchmark_context is None:
            benchmark_context = []
        else:
            # prepend prefix for internal validation
            benchmark_context = lmap(lambda x: self.prefix + "_context=" + x,
                                     benchmark_context)
        # supply the ref by default.
        benchmark_context += [f"--benchmark_context=ref={ref}"]
        if benchmark_filter is not None:
            flags.append(f"{prefix}_filter={benchmark_filter}")

        flags.append(f"{prefix}_repetitions={num_repetitions}")
        # Add benchmark context information like shown in
        # https://github.com/google/benchmark/blob/main/docs/user_guide.md#extra-context
        runner_util.validate_context(benchmark_context)
        flags += benchmark_context
        return flags

    def get_current_context(self) -> List[str]:
        ctx_info = [
            "--benchmark_context={0}={1}".format(*ctx()) for ctx in
            self.context_providers]
        return ctx_info

    def dispatch(
            self,
            benchmark: str,
            environment: BenchmarkEnvironment,
            repetitions: int = 1,
            run_as_module: bool = False,
            benchmark_filter: Optional[str] = None,
            benchmark_context: Optional[List[str]] = None) -> Tuple[int, str]:
        """Runner class method responsible for dispatching a benchmark run
        in a single target file. A subprocess will be spawned executing the
        benchmark in the given environment."""
        python = environment.get_value("python.executable")

        if run_as_module:
            module_name = convert_to_module(benchmark)
            command = [python, "-m", module_name]
        else:
            command = [python, benchmark]

        command += self.create_flags(
            environment=environment,
            num_repetitions=repetitions,
            benchmark_filter=benchmark_filter,
            benchmark_context=benchmark_context)

        return run_subprocess(command, errors="ignore")

    def run_benchmark(self,
                      argv: List[str] = None,
                      context: Dict[str, Any] = None) -> int:
        raise NotImplementedError
