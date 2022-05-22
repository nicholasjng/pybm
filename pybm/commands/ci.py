from typing import List

from pybm.command import CLICommand
from pybm.mixins.filemanager import WorkspaceManagerContextMixin
from pybm.statuscodes import ERROR, SUCCESS

# import yaml


def construct_workspace():
    pass


class CICommand(WorkspaceManagerContextMixin, CLICommand):
    """
    Run benchmark workloads in a continuous integration setting.
    """

    usage = "pybm ci <refs> [<options>]\n"

    def __init__(self):
        super(CICommand, self).__init__(name="ci")

    def add_arguments(self):
        self.parser.add_argument(
            "refs",
            nargs="*",
            default=None,
            help="Git references to benchmark.",
        )
        self.parser.add_argument(
            "-f",
            "--file",
            dest="ci_file",
            help="YAML file containing the desired state for the benchmark run.",
        )

    def run(self, args: List[str]) -> int:
        if not args:
            self.parser.print_help()
            return ERROR

        self.add_arguments()
        #
        # options = self.parser.parse_args(args)
        #
        # verbose: bool = options.verbose
        # ci_file: str = options.ci_file
        #
        # with open(ci_file, "r") as fp:
        #     cfg = yaml.load(fp, Loader=yaml.FullLoader)
        #
        # TODO: Validate config
        #
        # with self.main_context(verbose=verbose, readonly=False):
        #     pass
        #     benchmarks = cfg["benchmarks"]
        #     workspaces = cfg["workspaces"]

        return SUCCESS
