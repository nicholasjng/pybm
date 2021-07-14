import sys
from typing import Optional, List

from pybm.command import CLICommand
from pybm.parsers import parse_args, parse_command

def main(args: Optional[List[str]] = None) -> int:
    if not args:
        # first argv is absolute script path
        args = sys.argv[1:]

    command_name, command_args = parse_args(args)

    command: CLICommand = parse_command(command_name)

    return command.run(command_args)
