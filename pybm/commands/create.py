from pybm.command import CLICommand


class CreateCommand(CLICommand):
    """
    Create a pybm benchmark environment.
    """
    usage = "pybm create [<commit-ish>] [<dest>] [<options>]"

    def __init__(self, name: str):
        super(CreateCommand, self).__init__(name=name)

    def add_arguments(self):
        pass

    def run(self, *args, **kwargs) -> int:

        self.parser.parse_args(*args)

        return 0
