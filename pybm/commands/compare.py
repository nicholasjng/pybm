from typing import List

from pybm import PybmConfig
from pybm.command import CLICommand
from pybm.config import get_component_class
from pybm.reporters import BaseReporter
from pybm.status_codes import ERROR, SUCCESS
from pybm.util.path import get_subdirs


class CompareCommand(CLICommand):
    """
    Report benchmark results from specified sources.
    """

    usage = "pybm compare <refs> [<options>]\n"

    def __init__(self):
        super(CompareCommand, self).__init__(name="compare")
        self.config = PybmConfig.load()

    def add_arguments(self):
        # positionals
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

        reporter: BaseReporter = get_component_class("reporter", config=self.config)

        reporter_args = reporter.additional_arguments()

        if reporter_args:
            reporter_name = self.config.get_value("reporter.name")
            reporter_group_desc = (
                f"Additional options from configured reporter class {reporter_name!r}"
            )
            reporter_group = self.parser.add_argument_group(reporter_group_desc)
            # add builder-specific options into the group
            for arg in reporter_args:
                reporter_group.add_argument(arg.pop("flags"), **arg)

    def run(self, args: List[str]) -> int:
        if not args:
            self.parser.print_help()
            return ERROR

        self.add_arguments()

        options = self.parser.parse_args(args)

        reporter: BaseReporter = get_component_class("reporter", config=self.config)

        refs: List[str] = options.refs
        n_previous: int = options.include_previous
        report_absolutes: bool = options.absolute

        result_dir = reporter.result_dir
        results = sorted(get_subdirs(result_dir), key=int)[-n_previous:]

        reporter.compare(
            *refs,
            results=results,
            report_absolutes=report_absolutes,
            target_filter=options.target_filter,
            benchmark_filter=options.benchmark_filter,
            context_filter=options.context_filter,
        )

        return SUCCESS
