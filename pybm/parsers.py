import sys
from typing import List, Tuple

from pybm.command import CLICommand
from pybm.commands import command_db
from pybm.exceptions import CommandError, ArgumentError

# CLI command prefix for pybm
cmd_prefix = "-"

def parse_args(args: List[str]) -> Tuple[str, List[str]]:
    """
    Process the arguments passed to the pybm CLI main entrypoint.

    This function only checks syntactic correctness, it is not responsible
    for checking whether the given values for CLI options are actually
    valid.
    """

    # TODO: Refactor this branch based on likelihood of single option call
    # check block for pybm + single option call
    if len(args) < 2:
        # bare pybm call with no arguments
        if not args:
            return "base", args

        # not args == False <=> len(args) > 0
        opt = args[0]
        if not opt.startswith(cmd_prefix):
            raise ArgumentError(f"unknown option {opt} "
                                f"encountered for command \"pybm\"")
        else:
            return "base", args
    else:
        command_name, *command_args = args

        return command_name, command_args


def parse_command(command_name: str) -> CLICommand:
    # unknown command
    if command_name not in command_db:
        # TODO: Print similar commands if any, or print options
        raise CommandError(f"unknown command {command_name}")

    return command_db[command_name]


command_database = {
    # top level: commands
    "create": {
        # program name (pybm [COMMAND])
        "prog": "create",
        "description": "Create a pybm benchmark environment.",
        "usage": "pybm create [<commit-ish>] [<dest>] [<options>]",
        # arguments, either string or comma-separated string list for aliases
        # (e.g. -d,--delete for a delete flag and shorthand)
        "arguments": ["-p"]
    },
    "update": {

    },
    "destroy": {

    },
    "run": {

    },
    "set": {

    },
}

argument_store = {
    "--commit-ish": {
        "nargs": "+",
        "help": "Git refs to create worktrees for"
    },
    "-p": {
        "nargs": 1,
        "help": "Python executable used to create the virtual environment.",
        "default": sys.executable,
        "metavar": None,
        "choices": None,
    },
}
