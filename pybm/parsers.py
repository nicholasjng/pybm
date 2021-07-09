import argparse
from pybm import __version__
from pybm.exceptions import CommandError

def get_command_parser(command_name: str) -> argparse.ArgumentParser:
    if command_name not in command_database:
        raise CommandError(f"unknown command: {command_name}")

    command_data = command_database[command_name]
    arguments = command_data.pop("arguments")
    parser = argparse.ArgumentParser(**command_data)
    for arg, opts in arguments.items():
        parser.add_argument(arg, **opts)
    return parser


command_database = {
    # top level: commands
    "create": {
        # program name (pybm [COMMAND])
        "prog": "create",
        "description": "Create a pybm benchmark environment.",
        "usage": "pybm create [<commit-ish>] [<dest>] [<options>]",
        # options
        "arguments": {
            "-p": {
                "nargs": 1,
                "help": None,
                "default": None,
                "metavar": None,
                "choices": None,
            },

        }
    },
    "update": {

    },
    "destroy": {

    },
    "run": {

    },
    # version command
    "--version": {
        "arguments": {
            "--version": {
                # special argparse action for version printing
                "action": "version",
                "version": f"%(prog)s version {__version__}"
            }

        }
    }
}
