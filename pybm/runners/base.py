import argparse
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pybm.runners.util as runner_util
from pybm.config import config
from pybm.exceptions import PybmError
from pybm.specs import Package
from pybm.util.common import lmap
from pybm.util.imports import convert_to_module_name
from pybm.util.subprocess import run_subprocess
from pybm.workspace import Workspace

# A context provider produces name and value of a contextual
# piece of information, e.g. processor architecture, cwd etc.
ContextProvider = Callable[[], Tuple[str, str]]


class BaseRunner:
    """Base class for all pybm benchmark runners."""

    def __init__(self, name: str = "base"):
        self.name = name
        self.prefix = "--benchmark"

        # required packages for the runner
        self._required: List[Package] = [
            Package(name="pybm", origin="git+https://github.com/nicholasjng/pybm")
        ]

        # result saving directory; create if non-existent
        self.result_dir: str = config.get_value("core.resultdir")
        Path(self.result_dir).mkdir(parents=True, exist_ok=True)

        self.fail_fast: bool = config.get_value("runner.failfast")
        self.context_providers: List[
            ContextProvider
        ] = runner_util.load_context_providers(
            config.get_value("runner.contextproviders")
        )

    def check_required_packages(self, workspace: Workspace):
        missing_pkgs = []

        installed = workspace.packages
        names_and_versions = dict(lmap(lambda x: x.split("=="), installed))

        for package in self.required_packages:
            name, version = package.name, package.version
            if name not in names_and_versions:
                missing_pkgs.append(str(package))
            elif package.version is not None and names_and_versions[name] != version:
                missing_pkgs.append(str(package))

        if len(missing_pkgs) > 0:
            raise PybmError(
                f"Required packages {', '.join(missing_pkgs)} for runner class "
                f"pybm.runners.{self.__class__.__name__} not installed in workspace "
                f"{workspace.name!r}. To install them, run `pybm workspace install "
                f"{workspace.name} {' '.join(missing_pkgs)}`."
            )

    def create_flags(
        self,
        workspace: Workspace,
        repetitions: int = 1,
        benchmark_filter: Optional[str] = None,
        benchmark_context: Optional[List[str]] = None,
        **runner_kwargs,
    ) -> List[str]:
        flags, prefix = [], self.prefix
        ref, _ = workspace.get_ref_and_type()
        commit = workspace.commit

        if benchmark_context is None:
            benchmark_context = []
        else:
            # prepend prefix for internal validation
            benchmark_context = lmap(
                lambda x: f"{prefix}_context=" + x, benchmark_context
            )
        # supply the ref and commit by default.
        benchmark_context += [f"{prefix}_context=ref={ref}"]
        benchmark_context += [f"{prefix}_context=commit={commit}"]

        if benchmark_filter is not None:
            flags.append(f"{prefix}_filter={benchmark_filter}")

        flags.append(f"{prefix}_repetitions={repetitions}")

        for k, v in runner_kwargs.items():
            if isinstance(v, bool):
                # use safe boolean parsing ('true/false') to support Google Benchmark
                flags.append(f"{prefix}_{k}={str(v).lower()}")
            else:
                flags.append(f"{prefix}_{k}={v}")

        # Add benchmark context information like shown in
        # https://github.com/google/benchmark/blob/main/docs/user_guide.md#extra-context
        runner_util.validate_context(benchmark_context)
        flags += benchmark_context
        flags += [f"--runner={self.name}"]

        return flags

    def dispatch(
        self,
        benchmark: str,
        workspace: Workspace,
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
        python = workspace.executable
        worktree_root = workspace.root

        if run_as_module:
            module_name = convert_to_module_name(benchmark)
            command = [python, "-m", module_name]
        else:
            command = [python, benchmark]

        command += self.create_flags(
            workspace=workspace,
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

        def _safe_bool(s: str) -> bool:
            """
            Interpret 'true' as true, 'false' as false, everything else is an error.
            """
            if s.lower() == "true":
                return True
            elif s.lower() == "false":
                return False
            else:
                raise ValueError(f"illegal input {s!r}")

        # parts of the general benchmark runner spec
        parser.add_argument(f"{prefix}_repetitions", type=int)
        parser.add_argument(f"{prefix}_filter", type=str, default=None)
        parser.add_argument(f"{prefix}_context", action="append", default=None)
        parser.add_argument(
            f"{prefix}_enable_random_interleaving", type=_safe_bool, default=False
        )
        parser.add_argument(
            f"{prefix}_report_aggregates_only", type=_safe_bool, default=False
        )

        return parser.parse_args(flags)

    @property
    def required_packages(self) -> List[Package]:
        return self._required

    def run_benchmark(
        self, argv: List[str], module_context: Dict[str, Any] = None
    ) -> int:
        raise NotImplementedError
