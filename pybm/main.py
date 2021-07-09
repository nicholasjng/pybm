import sys
from typing import Optional, List

from pybm.command import CLICommand

def main(args: Optional[List[str]] = None) -> int:
    if not args:
        args = sys.argv[1:]
    command_name = args[0]
    # TODO: Get command from factory
    command: CLICommand = CLICommand(command_name)
    cmd_args = command.parse_args(args)

    return command.run(cmd_args)
