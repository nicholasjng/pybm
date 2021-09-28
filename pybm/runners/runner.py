import argparse
from typing import Optional, Tuple, Callable, List, Any, Union, Dict
from pathlib import Path

from pybm import PybmConfig
from pybm.exceptions import PybmError
from pybm.mixins import SubprocessMixin
from pybm.specs import BenchmarkEnvironment
from pybm.util.common import lfilter, lmap
from pybm.util.functions import is_context_provider
from pybm.util.imports import import_from_module
from pybm.util.path import list_contents, get_subdirs

# A context provider produces name and value of a contextual
# piece of information, e.g. processor architecture, cwd etc.
ContextProvider = Callable[[], Tuple[str, str]]


def is_glob_expression(expr: Union[str, Path]) -> bool:
    return "*" in str(expr)


class BenchmarkRunner(SubprocessMixin):
    """Base class for all pybm benchmark runners."""

    def __init__(self, config: PybmConfig):
        super().__init__()
        self.prefix = "--benchmark"

        # required packages for the runner
        self.required_packages = []

        self.result_dir: str = config.get_value("runner.resultDirectory")
        self.fail_fast: bool = config.get_value("runner.failFast")
        self.context_providers: List[ContextProvider] = \
            self.load_context_providers(config.get_value(
                "runner.contextProviders"))

    def create_flags(
            self,
            result_file: Union[str, Path],
            num_repetitions: int = 1,
            benchmark_filter: Optional[str] = None,
            benchmark_context: Optional[List[str]] = None) -> List[str]:
        prefix = self.prefix
        # JSON is the only supported output file format in GBM
        flags = [f"{prefix}_out={result_file}",
                 f"{prefix}_out_format=json"]
        if benchmark_context is None:
            benchmark_context = []
        if benchmark_filter is not None:
            flags.append(f"{prefix}_filter={benchmark_filter}")
        if num_repetitions > 1:
            flags.append(f"{prefix}_repetitions={num_repetitions}")
        # Add benchmark context information like shown in
        # https://github.com/google/benchmark/blob/main/docs/user_guide.md#extra-context
        self.validate_context(benchmark_context)
        flags += benchmark_context
        return flags

    def create_parser(self):
        prefix = self.prefix
        parser = argparse.ArgumentParser(prog=self.__class__.__name__,
                                         add_help=False)
        parser.add_argument(f"{prefix}_out",
                            type=str,
                            default=None)
        parser.add_argument(f"{prefix}_out_format",
                            type=str,
                            choices=("json", "console"),
                            default=None)
        parser.add_argument(f"{prefix}_filter",
                            type=str,
                            default=None)
        parser.add_argument(f"{prefix}_repetitions",
                            type=int,
                            default=1)
        parser.add_argument(f"{prefix}_context",
                            action="append",
                            default=None)
        return parser

    def parse_flags(self, flags: List[str]):
        parser = self.create_parser()
        option_dict = vars(parser.parse_args(flags))
        return option_dict

    def create_result_dir(self, environment: BenchmarkEnvironment) -> Path:
        subdirs = sorted(get_subdirs(self.result_dir))
        ref, _ = environment.worktree.get_ref_and_type()
        if not subdirs:
            folder = "1"
        else:
            folder = str(int(subdirs[-1]) + 1)
        result_path = Path(self.result_dir) / folder
        # this method is called on dispatch, so the directory will only be
        # created on the first target's dispatch call
        result_path.mkdir(parents=True, exist_ok=True)
        result_ref_dir = result_path / ref
        assert not result_ref_dir.exists()
        return result_ref_dir

    def get_current_context(self) -> List[str]:
        ctx_info = [
            "--benchmark_context={0}={1}".format(*ctx()) for ctx in
            self.context_providers]
        return ctx_info

    @staticmethod
    def find_targets(path: Union[str, Path]):
        benchmark_path = Path(path)
        if benchmark_path.is_dir():
            benchmark_targets = list_contents(benchmark_path,
                                              file_suffix=".py")
        elif benchmark_path.is_file():
            benchmark_targets = list(str(path))
        elif is_glob_expression(benchmark_path):
            ppath, glob = benchmark_path.parent, benchmark_path.name
            benchmark_targets = lmap(str, ppath.glob(glob))
        else:
            benchmark_targets = []
        return benchmark_targets

    @staticmethod
    def load_context_providers(provider_info: str) -> List[Any]:
        if provider_info != "":
            provider_names = provider_info.split(",")
        else:
            return []
        # require the context providers to come from an installed module
        imported = [import_from_module(name) for name in provider_names]
        return lfilter(is_context_provider, imported)

    def check_required_packages(self, environment: BenchmarkEnvironment):
        missing_pkgs = []
        for pkg in self.required_packages:
            if pkg not in environment.get_value("python.packages"):
                missing_pkgs.append(pkg)
        if len(missing_pkgs) > 0:
            raise PybmError(f"Required packages {', '.join(missing_pkgs)} "
                            f"for runner {self.__class__.__name__} not "
                            f"installed in environment {environment.name!r}. "
                            f"To install them, run `pybm env install "
                            f"{environment.name} {' '.join(missing_pkgs)}`.")

    @staticmethod
    def validate_context(context: List[str]):
        for ctx_val in context:
            seen: Dict[str, str] = {}
            split_ctx = ctx_val.split("=")
            if len(split_ctx) != 3:
                raise PybmError("Could not properly parse context value "
                                f"{ctx_val!r}. Context values need to be "
                                f"given as arguments in the format "
                                f"\"--context=<key>=<value>\".")
            name, value = split_ctx[1:]
            if name in seen:
                raise PybmError(f"Multiple values for context value "
                                f"{name!r} were supplied. Perhaps you "
                                f"gave some context information twice, "
                                f"once on the command line as global context, "
                                f"and via a set environment-specific context "
                                f"provider. To check the currently set "
                                f"environment-specific context providers, "
                                f"run the command "
                                f"`pybm config get runner.contextProviders`.")

    def dispatch(
            self,
            benchmarks: List[str],
            environment: BenchmarkEnvironment,
            repetitions: int = 1,
            benchmark_filter: Optional[str] = None,
            benchmark_context: Optional[List[str]] = None):
        raise NotImplementedError

    def run_benchmark(self, args: List[str] = None) -> int:
        raise NotImplementedError
