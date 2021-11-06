from typing import List

from pybm import PybmConfig
from pybm.command import CLICommand
from pybm.config import get_reporter_class
from pybm.exceptions import PybmError
from pybm.reporters.base import BenchmarkReporter
from pybm.status_codes import ERROR, SUCCESS
from pybm.util.path import get_subdirs


class CompareCommand(CLICommand):
    """
    Report benchmark results from specified sources.
    """

    usage = "pybm compare <run> <anchor-ref> <compare-refs> [<options>]\n"

    def __init__(self):
        super(CompareCommand, self).__init__(name="compare")
        self.config = PybmConfig.load(".pybm/config.yaml")

    def add_arguments(self):
        self.parser.add_argument(
            "run",
            type=str,
            metavar="<run>",
            help="Benchmark run to report results for. "
            "To report the preceding run, use the "
            '"latest" keyword. To report results '
            "of the n-th preceding run "
            "(i.e., n runs ago), "
            'use the "latest^{n}" syntax.',
        )
        self.parser.add_argument(
            "refs",
            nargs="+",
            metavar="<refs>",
            help="Benchmarked refs to compare. The first "
            "given ref will be treated as the "
            "anchor ref, relative to which all "
            "differences are reported. An error is "
            "raised if any of the given "
            "refs are not present in the run.",
        )

        reporter: BenchmarkReporter = get_reporter_class(config=self.config)
        reporter_name = self.config.get_value("reporter.className")
        reporter_group_desc = (
            f"Additional options from configured reporter class {reporter_name!r}"
        )
        reporter_group = self.parser.add_argument_group(reporter_group_desc)
        # add builder-specific options into the group
        for arg in reporter.add_arguments():
            reporter_group.add_argument(arg.pop("flags"), **arg)

    def run(self, args: List[str]) -> int:
        if not args:
            self.parser.print_help()
            return ERROR

        self.add_arguments()
        options = self.parser.parse_args(args)

        reporter: BenchmarkReporter = get_reporter_class(config=self.config)

        # TODO: Parse run to fit schema
        run = options.run
        refs: List[str] = options.refs

        result_dir = reporter.result_dir
        # TODO: Make this dynamic to support other run identifiers
        result = sorted(get_subdirs(result_dir))[-1]
        result_path = result_dir / result

        if result_path.exists():
            reporter.compare(
                *refs,
                result=result,
                target_filter=options.target_filter,
                benchmark_filter=options.benchmark_filter,
                context_filter=options.context_filter,
            )
        else:
            raise PybmError(
                f"No benchmark results found for the requested run {run!r}."
            )

        return SUCCESS
