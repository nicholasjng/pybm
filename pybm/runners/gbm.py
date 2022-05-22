from typing import Any, Dict, List

import pybm.runners.util as runner_util
from pybm import PybmError
from pybm.runners.base import BaseRunner
from pybm.specs import Package
from pybm.util.common import lfilter
from pybm.util.extras import get_extras

try:
    import google_benchmark as gbm
    from absl import app

    GBM_INSTALLED = True
except ImportError:
    GBM_INSTALLED = False


class GoogleBenchmarkRunner(BaseRunner):
    """
    A benchmark runner class interface designed to dispatch benchmark runs
    in pybm using Google Benchmark's Python bindings.
    """

    def __init__(self):
        if not GBM_INSTALLED:
            raise PybmError(
                "Missing dependencies. You attempted to use the Google Benchmark "
                "runner without having the required dependencies installed. "
                "\n"
                "To do so, please run the command `pybm workspace install main "
                f"{' '.join([str(p) for p in self.required_packages])}` in your "
                f"main virtual environment."
            )

        super().__init__(name="gbm")

    @property
    def required_packages(self) -> List[Package]:
        return get_extras()["gbm"]

    def run_benchmark(
        self, argv: List[str], module_context: Dict[str, Any] = None
    ) -> int:
        def flags_parser(argv: List[str]):
            argv = gbm.initialize(argv)
            return app.parse_flags_with_usage(argv)

        def run_benchmarks(argv: List[str] = None):
            return gbm.run_benchmarks()

        # inject environment-specific context into args
        argv += self.get_current_context()

        # JSON is the only supported output file format in GBM
        argv += [f"{self.prefix}_format=json"]

        runtime_context = lfilter(lambda x: x.startswith("--benchmark_context"), argv)

        runner_util.validate_context(runtime_context, parsed=False)

        return app.run(run_benchmarks, argv=argv, flags_parser=flags_parser)
