from typing import List

from pybm.command import CLICommand
from pybm import __version__

from pybm.status_codes import SUCCESS, ERROR


class BaseCommand(CLICommand):
    """
    Commands:

    env     - Create and manage benchmarking environments.
    apply   - Run a benchmarking workflow specified in a YAML file.
    """
    usage = "pybm [--version] [-h, --help]"

    def __init__(self, name: str):
        super(BaseCommand, self).__init__(
            name=name,
        )

    def add_arguments(self):
        # special version action and version kwarg
        self.parser.add_argument("--version",
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
