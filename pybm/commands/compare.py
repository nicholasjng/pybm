from typing import List

from pybm.command import CLICommand
from pybm.config import get_component
from pybm.reporters import BaseReporter
from pybm.statuscodes import ERROR, SUCCESS

time_unit_choices = ("s", "sec", "ms", "msec", "us", "usec", "ns", "nsec")


class CompareCommand(CLICommand):
    """
    Report and compare benchmark results from specified sources.
    """

    usage = "pybm compare <refs> [<options>]\n"

    def __init__(self):
        super(CompareCommand, self).__init__(name="compare")

    def add_arguments(self):
        # positionals
        self.parser.add_argument(
            "refs",
            nargs="+",
            metavar="<refs>",
            help="Benchmarked refs to compare. The first given ref is treated as the "
            "anchor, relative to which all differences are reported.",
        )
        self.parser.add_argument(
            "-I",
            "--include-previous",
            type=int,
            default=1,
            dest="previous",
            metavar="<N>",
            help="How many previous runs to including in result comparison. Defaults "
            "to 1, which compares only the latest benchmark run.",
        )
        self.parser.add_argument(
            "--absolute",
            action="store_true",
            default=False,
            help="Report absolute numbers instead of relative differences.",
        )
        self.parser.add_argument(
            "--time-unit",
            type=str,
            default=None,
            choices=time_unit_choices,
            help="Time unit to display benchmark results in.",
        )
        self.parser.add_argument(
            "--digits",
            type=int,
            default=None,
            help="Significant digits to display for floating point results, including "
            "time.",
        )
        self.parser.add_argument(
            "--as-integers",
            action="store_true",
            default=False,
            help="Display all floating point results as integers, rounding them in "
            "the process.",
        )
        self.parser.add_argument(
            "--shalength",
            type=int,
            default=None,
            help="Number of hex digits to display for git reference SHA values.",
        )
        self.parser.add_argument(
            "--sort-by",
            type=str,
            default=None,
            help="Key and mode (asc/desc) to sort results by. Needs to be "
            "formatted as 'key: mode' (e.g. speedup: asc).",
        )
        self.parser.add_argument(
            "--target-filter",
            type=str,
            default=None,
            metavar="<regex>",
            help="Regex filter to selectively filter benchmark target files. If "
            "specified, only benchmark files matching the given regex will be "
            "included in the report.",
        )
        self.parser.add_argument(
            "--benchmark-filter",
            type=str,
            default=None,
            metavar="<regex>",
            help="Regex filter to selectively report benchmarks from the matched "
            "target files. If specified, only benchmarks matching the given regex "
            "will be included in the report.",
        )
        self.parser.add_argument(
            "--context-filter",
            type=str,
            default=None,
            metavar="<regex>",
            help="Regex filter for additional context to report from the benchmarks. "
            "If specified, context values matching the given regex will be included "
            "in the report.",
        )

    def run(self, args: List[str]) -> int:
        if not args:
            self.parser.print_help()
            return ERROR

        self.add_arguments()

        options = self.parser.parse_args(args)

        reporter: BaseReporter = get_component("reporter")

        refs: List[str] = options.refs

        reporter.compare(
            *refs,
            absolute=options.absolute,
            previous=options.previous,
            sort_by=options.sort_by,
            time_unit=options.time_unit,
            digits=options.digits,
            as_integers=options.as_integers,
            shalength=options.shalength,
            target_filter=options.target_filter,
            benchmark_filter=options.benchmark_filter,
            context_filter=options.context_filter,
        )

        return SUCCESS
