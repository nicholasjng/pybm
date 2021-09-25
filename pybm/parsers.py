from typing import List, Tuple

from pybm.command import CLICommand
from pybm.commands import command_db
from pybm.exceptions import CommandError

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
            return opt, []
        else:
            return "base", args
    else:
        # TODO: Think about how to extend this eventually to subcommands
        command_name, *command_args = args

        return command_name, command_args


def parse_command(command_name: str) -> CLICommand:
    # unknown command
    if command_name not in command_db:
        # TODO: Print similar commands if any, or print options
        raise CommandError(f"Unknown command {command_name}")

    return command_db[command_name]()
