import sys
from typing import List, Optional, Dict, Any

import pybm.runners.util as runner_util
from pybm import PybmError
from pybm.config import PybmConfig
from pybm.runners.base import BaseRunner
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

    def __init__(self, config: PybmConfig):
        self.required_packages = get_extras()["gbm"]
        if not GBM_INSTALLED:
            raise PybmError(
                "Missing dependencies. You attempted to use the "
                "Google Benchmark runner without having the "
                "required dependencies installed. To do so, "
                "please run the command `pybm env install root "
                f"{' '.join(self.required_packages)}` while "
                f"inside your root virtual environment.\n "
                f"BEWARE: As of 10/2021, Google Benchmark does "
                f"not have source wheels available for any "
                f"platforms outside of Linux, and Python versions "
                f"outside of Python 3.6-3.8. If you want to use "
                f"Google Benchmark on any platform or Python "
                f"interpreter outside this group, you will have "
                f"to build the wheel from source. This requires "
                f"Bazel; for information on Bazel installation, see "
                f"https://docs.bazel.build/versions/4.2.1/install.html."
            )

        super().__init__(config=config)

    def additional_arguments(self):
        return [
            {
                "flags": "--enable-random-interleaving",
                "type": bool,
                "action": "store_true",
                "default": False,
                "help": "Whether to enable the random interleaving feature "
                "in Google Benchmark. This can reduce run-to-run "
                "variance by running benchmarks in random order.",
            },
            {
                "flags": "--report-aggregates-only",
                "type": bool,
                "action": "store_true",
                "default": False,
                "help": "Whether to report aggregates (mean/stddev) only "
                "in Google Benchmark instead of the raw data.",
            },
        ]

    def run_benchmark(
        self, argv: Optional[List[str]] = None, context: Dict[str, Any] = None
    ) -> int:
        def flags_parser(argv: List[str]):
            argv = gbm.initialize(argv)
            return app.parse_flags_with_usage(argv)

        def run_benchmarks(argv: List[str] = None):
            return gbm.run_benchmarks()

        argv = argv or sys.argv

        # inject environment-specific context into args
        argv += self.get_current_context()

        # JSON is the only supported output file format in GBM
        argv += [f"{self.prefix}_format=json"]

        runtime_context = lfilter(lambda x: x.startswith("--benchmark_context"), argv)

        runner_util.validate_context(runtime_context, parsed=False)

        return app.run(run_benchmarks, argv=argv, flags_parser=flags_parser)
