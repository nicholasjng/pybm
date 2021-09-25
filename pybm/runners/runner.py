from typing import Sequence, Optional, Tuple, Callable, List, Any

from pybm import PybmConfig
from pybm.exceptions import PybmError
from pybm.mixins import SubprocessMixin
from pybm.specs import BenchmarkEnvironment
from pybm.util.common import lfilter
from pybm.util.functions import is_context_provider
from pybm.util.imports import import_from_module

# A context provider produces name and value of a contextual
# piece of information, e.g. processor architecture, cwd etc.
ContextProvider = Callable[[], Tuple[str, str]]


class BenchmarkRunner(SubprocessMixin):
    """Base class for all pybm benchmark runners."""

    def __init__(self, config: PybmConfig):
        super().__init__(exception_type=PybmError)
        self.required_packages: list[str] = config.get_value(
            "runner.requiredPackages")
        self.output_dir: str = config.get_value("runner.resultDirectory")
        self.fail_fast: bool = config.get_value("runner.failFast")
        self.context_providers: List[ContextProvider] = \
            self.load_context_providers(config.get_value(
                "runner.contextProviders")
            )

    @staticmethod
    def load_context_providers(provider_info: str) -> List[Any]:
        if provider_info != "":
            provider_names = provider_info.split(",")
        else:
            return []
        imported = [import_from_module(name) for name in provider_names]
        return lfilter(is_context_provider, imported)

    def check_required_packages(self, environment: BenchmarkEnvironment) \
            -> None:
        missing_pkgs = []
        for pkg in self.required_packages:
            if pkg not in environment.venv.packages:
                missing_pkgs.append(pkg)
        if len(missing_pkgs) > 0:
            pkgs = " ".join(missing_pkgs)
            raise PybmError(f"Required packages \"{pkgs}\" not installed "
                            f"in environment {environment.name!r}. "
                            f"To install them, run `pybm env install "
                            f"{environment.name} {pkgs}`.")

    def run_benchmarks(
            self,
            benchmarks: Sequence[str],
            environment: BenchmarkEnvironment,
            benchmark_filter: Optional[str] = None,
            context_providers: Optional[Sequence[ContextProvider]] = None):
        raise NotImplementedError
