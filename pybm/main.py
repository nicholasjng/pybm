import os
import sys
from typing import List, Optional

from pybm.command import CLICommand
from pybm.commands import CommandMapping
from pybm.exceptions import CommandError, GitError, PythonError
from pybm.statuscodes import ERROR

error_origins: dict[type[Exception], str] = {
    GitError: "git",
    PythonError: "python",
}

# CLI flag prefix for pybm
prefix = "-"


def main(args: Optional[List[str]] = None) -> int:
    # first element of sys.argv is absolute script path
    args = args or sys.argv[1:]

    if not args or args[0].startswith(prefix):
        command = ""
    else:
        command, *args = args

    try:
        if command not in CommandMapping:
            # TODO: Print similar commands if any, or print options
            raise CommandError(f"Unknown command {command!r}")

        cmd: CLICommand = CommandMapping[command]()
        return cmd.run_wrapped(args)
    except Exception as e:
        origin = error_origins.get(type(e), "pybm")
        sys.stderr.write(f"{origin}: {e}")
        sys.stderr.write(os.linesep)
        return ERROR
