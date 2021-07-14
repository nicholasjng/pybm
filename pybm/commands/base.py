from pybm.command import CLICommand
from pybm import __version__


class BaseCommand(CLICommand):
    """
    The most common commands for pybm:
    """
    usage = None

    def __init__(self, name: str):
        super(BaseCommand, self).__init__(name=name)

    def add_arguments(self):
        # special version action and version kwarg
        self.parser.add_argument("--version",
                                 action="version",
                                 version=f"%(prog)s version {__version__}")

    def run(self, *args, **kwargs):

        self.add_arguments()

        _ = self.parser.parse_args(*args)

        return 0
