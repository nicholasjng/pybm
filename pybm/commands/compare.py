from typing import List

from pybm.command import CLICommand
from pybm.config import get_component
from pybm.reporters import BaseReporter
from pybm.status_codes import ERROR, SUCCESS


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
            "anchor ref, relative to which all differences are reported. An error is "
            "raised if any of the given refs are not present in the run.",
        )

        # optionals
        self.parser.add_argument(
            "-I",
            "--include-previous",
            type=int,
            default=1,
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
        previous: int = options.include_previous
        absolute: bool = options.absolute

        reporter.compare(
            *refs,
            absolute=absolute,
            previous=previous,
            target_filter=options.target_filter,
            benchmark_filter=options.benchmark_filter,
            context_filter=options.context_filter,
        )

        return SUCCESS
