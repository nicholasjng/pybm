from typing import List

from pybm import __version__
from pybm.command import CLICommand
from pybm.status_codes import SUCCESS, ERROR


class BaseCommand(CLICommand):
    """
    Commands:

    apply   - Run a benchmarking workflow specified in a YAML file.
    compare - Compare benchmark results between different git references.
    config  - Display and change pybm configuration values.
    env     - Create and manage benchmarking environments.
    init    - Initialize a git repository for pybm benchmarking.
    run     - Run specified benchmarks in different environments.
    """

    usage = "pybm <command> [<options>]"

    def __init__(self):
        super(BaseCommand, self).__init__(name="")

    def add_arguments(self):
        # special version action and version kwarg
        self.parser.add_argument(
            "--version",
            action="version",
            help="Show pybm version and exit.",
            version=f"%(prog)s version {__version__}",
        )

    def run(self, args: List[str]):
        self.add_arguments()

        if not args:
            self.parser.print_help()
            return ERROR

        options = self.parser.parse_args(args)

        if options.verbose:
            print(vars(options))

        return SUCCESS
