import os
import sys
from typing import Optional, List

from pybm.command import CLICommand
from pybm.exceptions import CommandError, PybmError
from pybm.parsers import parse_args, parse_command


def main(args: Optional[List[str]] = None) -> int:
    if not args:
        # first argv is absolute script path
        args = sys.argv[1:]

    command_name, command_args = parse_args(args)

    try:
        command: CLICommand = parse_command(command_name)
    except (CommandError, PybmError) as e:
        sys.stderr.write(f"Error: {e}")
        sys.stderr.write(os.linesep)
        sys.exit(1)

    return command.run_wrapped(command_args)
