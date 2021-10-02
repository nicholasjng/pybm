from pathlib import Path
from typing import Optional, Tuple, Callable, List, Any, Union, Dict

import pybm.runners.util as runner_util
from pybm import PybmConfig
from pybm.exceptions import PybmError
from pybm.mixins import SubprocessMixin
from pybm.specs import BenchmarkEnvironment
from pybm.util.common import lfilter, lmap
from pybm.util.path import list_contents

# A context provider produces name and value of a contextual
# piece of information, e.g. processor architecture, cwd etc.
ContextProvider = Callable[[], Tuple[str, str]]


class BenchmarkRunner(SubprocessMixin):
    """Base class for all pybm benchmark runners."""

    def __init__(self, config: PybmConfig):
        super().__init__()
        self.prefix = "--benchmark"

        # required packages for the runner
        self.required_packages: list[str] = []

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
            num_repetitions: int = 5,
            benchmark_filter: Optional[str] = None,
            benchmark_context: Optional[List[str]] = None) -> List[str]:
        flags, prefix = [], self.prefix

        if benchmark_context is None:
            benchmark_context = []
        else:
            # prepend prefix for internal validation
            benchmark_context = lmap(lambda x: self.prefix + "_context=" + x,
                                     benchmark_context)
        if benchmark_filter is not None:
            flags.append(f"{prefix}_filter={benchmark_filter}")

        flags.append(f"{prefix}_repetitions={num_repetitions}")
        # Add benchmark context information like shown in
        # https://github.com/google/benchmark/blob/main/docs/user_guide.md#extra-context
        runner_util.validate_context(benchmark_context)
        flags += benchmark_context
        return flags

    @staticmethod
    def find_targets(path: Union[str, Path]):
        benchmark_path = Path(path)
        if benchmark_path.is_dir():
            benchmark_targets = list_contents(benchmark_path,
                                              file_suffix=".py")
        elif benchmark_path.is_file():
            benchmark_targets = [str(path)]
        else:
            # assume it is a glob pattern
            ppath, glob = benchmark_path.parent, benchmark_path.name
            benchmark_targets = lmap(str, ppath.glob(glob))
        # filter out __init__.py files by default
        benchmark_targets = lfilter(lambda x: not x.endswith("__init__.py"),
                                    benchmark_targets)
        return benchmark_targets

    def get_current_context(self) -> List[str]:
        ctx_info = [
            "--benchmark_context={0}={1}".format(*ctx()) for ctx in
            self.context_providers]
        return ctx_info

    def dispatch(
            self,
            benchmark: Union[str, Path],
            environment: BenchmarkEnvironment,
            repetitions: int = 1,
            benchmark_filter: Optional[str] = None,
            benchmark_context: Optional[List[str]] = None) -> Tuple[int, str]:
        """Runner class method responsible for dispatching a benchmark run
        in a single target file. A subprocess will be spawned executing the
        benchmark in the given environment."""

        python = environment.get_value("python.executable")
        worktree_root = environment.get_value("worktree.root")
        ref, _ = environment.worktree.get_ref_and_type(bare=True)
        # supply the ref by default.
        command = [python, benchmark, f"--benchmark_context=ref={ref}"]
        command += self.create_flags(
            num_repetitions=repetitions,
            benchmark_filter=benchmark_filter,
            benchmark_context=benchmark_context,
        )
        return self.run_subprocess(command, reraise_on_error=False,
                                   cwd=worktree_root)

    def run_benchmark(self,
                      argv: List[str] = None,
                      context: Dict[str, Any] = None) -> int:
        raise NotImplementedError
