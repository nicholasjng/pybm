from pathlib import Path
from typing import Optional, Tuple, Callable, List, Any, Dict

import argparse
import pybm.runners.util as runner_util
from pybm import PybmConfig
from pybm.exceptions import PybmError
from pybm.specs import BenchmarkEnvironment
from pybm.util.common import lmap
from pybm.util.imports import convert_to_module_name
from pybm.util.subprocess import run_subprocess

# A context provider produces name and value of a contextual
# piece of information, e.g. processor architecture, cwd etc.
ContextProvider = Callable[[], Tuple[str, str]]


class BaseRunner:
    """Base class for all pybm benchmark runners."""

    def __init__(self, config: PybmConfig):
        super().__init__()
        self.prefix = "--benchmark"

        # required packages for the runner
        self.required_packages: List[str] = ["pybm"]

        # result saving directory; create if non-existent
        self.result_dir: str = config.get_value("core.resultdir")
        Path(self.result_dir).mkdir(parents=True, exist_ok=True)

        self.fail_fast: bool = config.get_value("runner.failfast")
        self.context_providers: List[
            ContextProvider
        ] = runner_util.load_context_providers(
            config.get_value("runner.contextproviders")
        )

    def additional_arguments(self):
        raise NotImplementedError

    def check_required_packages(self, environment: BenchmarkEnvironment):
        missing_pkgs = []

        installed = environment.get_value("python.packages")
        names_and_versions = dict(lmap(lambda x: x.split("=="), installed))

        for pkg in self.required_packages:
            if "==" not in pkg:
                name, version = pkg, ""
            else:
                name, version = pkg.split("==")

            if name not in names_and_versions:
                # TODO: Improve this to handle non-PyPI package installation
                if name == "pybm":
                    missing_pkgs.append("git+https://github.com/nicholasjng/pybm")
                else:
                    missing_pkgs.append(pkg)
            else:
                if version != "" and names_and_versions[name] != version:
                    missing_pkgs.append(pkg)

        if len(missing_pkgs) > 0:
            raise PybmError(
                f"Required packages {', '.join(missing_pkgs)} "
                f"for runner {self.__class__.__name__} not "
                f"installed in environment {environment.name!r}. "
                f"To install them, run `pybm env install "
                f"{environment.name} {' '.join(missing_pkgs)}`."
            )

    def create_flags(
        self,
        environment: BenchmarkEnvironment,
        repetitions: int = 1,
        benchmark_filter: Optional[str] = None,
        benchmark_context: Optional[List[str]] = None,
        **runner_kwargs,
    ) -> List[str]:
        flags, prefix = [], self.prefix
        ref, _ = environment.worktree.get_ref_and_type()

        if benchmark_context is None:
            benchmark_context = []
        else:
            # prepend prefix for internal validation
            benchmark_context = lmap(
                lambda x: f"{prefix}_context=" + x, benchmark_context
            )
        # supply the ref by default.
        benchmark_context += [f"{prefix}_context=ref={ref}"]

        if benchmark_filter is not None:
            flags.append(f"{prefix}_filter={benchmark_filter}")

        flags.append(f"{prefix}_repetitions={repetitions}")

        for k, v in runner_kwargs.items():
            if isinstance(v, bool):
                # leave out the value, presence of the flag implies "true"
                flags.append(f"{prefix}_{k}")
            else:
                flags.append(f"{prefix}_{k}={v}")

        # Add benchmark context information like shown in
        # https://github.com/google/benchmark/blob/main/docs/user_guide.md#extra-context
        runner_util.validate_context(benchmark_context)
        flags += benchmark_context

        return flags

    def dispatch(
        self,
        benchmark: str,
        environment: BenchmarkEnvironment,
        run_as_module: bool = False,
        repetitions: int = 1,
        benchmark_filter: Optional[str] = None,
        benchmark_context: Optional[List[str]] = None,
        **runner_kwargs,
    ) -> Tuple[int, str]:
        """
        Runner class method responsible for dispatching a benchmark run
        in a single target file. A subprocess will be spawned executing the
        benchmark in the given environment.
        """
        python = environment.get_value("python.executable")
        worktree_root = environment.get_value("worktree.root")

        if run_as_module:
            module_name = convert_to_module_name(benchmark)
            command = [python, "-m", module_name]
        else:
            command = [python, benchmark]

        command += self.create_flags(
            environment=environment,
            repetitions=repetitions,
            benchmark_filter=benchmark_filter,
            benchmark_context=benchmark_context,
            **runner_kwargs,
        )

        return run_subprocess(command, errors="ignore", cwd=worktree_root)

    def get_current_context(self) -> List[str]:
        """Getting Python-specific runtime context. This should be called inside the
        run_benchmark method inside the subprocess created by dispatch()."""
        ctx_info = [
            f"{0}_context={1}={2}".format(self.prefix, *ctx())
            for ctx in self.context_providers
        ]
        return ctx_info

    def parse_flags(self, flags: List[str]):
        prefix = self.prefix

        parser = argparse.ArgumentParser(prog=self.__class__.__name__, add_help=False)

        # parts of the general benchmark runner spec
        parser.add_argument(f"{prefix}_repetitions", type=int)
        parser.add_argument(f"{prefix}_filter", type=str, default=None)
        parser.add_argument(f"{prefix}_context", action="append", default=None)

        # runner-specific arguments
        for arg in self.additional_arguments():
            parser.add_argument(arg.pop("flags"), **arg)

        return parser.parse_args(flags)

    def run_benchmark(
        self, argv: Optional[List[str]] = None, context: Dict[str, Any] = None
    ) -> int:
        raise NotImplementedError
