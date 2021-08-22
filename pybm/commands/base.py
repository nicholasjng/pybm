from typing import Any, List

from pybm.command import CLICommand
from pybm import __version__

from pybm.status_codes import SUCCESS, ERROR


class BaseCommand(CLICommand):
    """
    The most common commands for pybm:

    pybm create  - Create a benchmarking environment.
    pybm destroy - Remove a stale benchmarking environment.
    pybm apply   - Run a benchmarking workflow specified in a YAML file.
    """
    usage = "pybm [--version] [-h, --help]"

    def __init__(self, name: str):
        super(BaseCommand, self).__init__(
            name=name,
        )

    def add_arguments(self):
        # special version action and version kwarg
        self.parser.add_argument("-V",
                                 "--version",
                                 action="version",
                                 help="show pybm version number and exit.",
                                 version=f"%(prog)s version {__version__}")

    def run(self, args: List[str]):
        self.add_arguments()

        if not args:
            self.parser.print_help()
            return ERROR

        opts = self.parser.parse_args(args)
        verbose = opts.v

        if verbose:
            print(vars(opts))

        return SUCCESS
