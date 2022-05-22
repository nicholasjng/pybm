import argparse
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Callable, List, Mapping

import yaml

from pybm.command import CLICommand
from pybm.config import GLOBAL_CONFIG, LOCAL_CONFIG, PybmConfig
from pybm.exceptions import PybmError
from pybm.statuscodes import ERROR, SUCCESS
from pybm.util.common import lpartition

EnvSubcommand = Callable[[argparse.Namespace], int]


class ConfigCommand(CLICommand):
    """Display and manipulate pybm configuration values."""

    usage = (
        "pybm config get <option>\n"
        "   or: pybm config set <option> <value>\n"
        "   or: pybm config list\n"
        "   or: pybm config describe <option>\n"
    )

    def __init__(self):
        super().__init__(name="config")

    def add_arguments(self, subcommand: str = None):
        # special version action and version kwarg
        if subcommand != "list":
            self.parser.add_argument(
                "option",
                type=str,
                metavar="<option>",
                help=f"Config option to {subcommand}. For a comprehensive list of "
                f"options, run `pybm config list`.",
            )

        if subcommand == "set":
            self.parser.add_argument(
                "value",
                metavar="<value>",
                help="New value to set for the chosen config option.",
            )

        self.parser.add_argument(
            "--global",
            action="store_true",
            default=False,
            dest="useglobal",
            help="Use the global config instead of the local one.",
        )

    @staticmethod
    def get(options: argparse.Namespace) -> int:
        attr: str = options.option
        path = GLOBAL_CONFIG if options.useglobal else LOCAL_CONFIG

        value = PybmConfig.load(path).get_value(attr)

        if value is None:
            return ERROR

        if is_dataclass(value):
            print(yaml.dump({attr: asdict(value)}))
        else:
            print(f"{attr} = {value}")

        return SUCCESS

    @staticmethod
    def set(options: argparse.Namespace) -> int:
        attr, value = str(options.option), str(options.value)
        useglobal: bool = options.useglobal
        path = Path(GLOBAL_CONFIG if useglobal else LOCAL_CONFIG)

        if useglobal and not Path(GLOBAL_CONFIG).exists():
            # to set the first global value, initialize with an empty dict
            cfg = PybmConfig.from_dict({})
        else:
            cfg = PybmConfig.load(path)

        cfg.set_value(attr, value)
        cfg.save(path)

        return SUCCESS

    @staticmethod
    def list(options: argparse.Namespace) -> int:
        path = GLOBAL_CONFIG if options.useglobal else LOCAL_CONFIG

        config = PybmConfig.load(path)

        print(config.to_string())

        return SUCCESS

    @staticmethod
    def describe(options: argparse.Namespace) -> int:
        attr: str = options.option
        path = GLOBAL_CONFIG if options.useglobal else LOCAL_CONFIG

        if attr.startswith("_"):
            raise PybmError(
                "Private attributes cannot be accessed via `pybm config describe`."
            )

        PybmConfig.load(path).describe(attr)

        return SUCCESS

    def run(self, args: List[str]):
        subcommand_handlers: Mapping[str, EnvSubcommand] = {
            "describe": self.describe,
            "get": self.get,
            "list": self.list,
            "set": self.set,
        }

        if not args or args[0] not in subcommand_handlers:
            self.parser.print_help()
            return ERROR

        subcommand, *args = args

        self.add_arguments(subcommand=subcommand)

        # double hyphen prevents `config set` values to be mistaken for
        # optional arguments (e.g. venv flags)
        # https://docs.python.org/3/library/argparse.html#arguments-containing
        if subcommand == "set":
            # Insert the double hyphen after flags, otherwise they break
            flag_names = ["-h", "--help", "-v", "--global"]
            flags, values = lpartition(lambda x: x in flag_names, args)
            options = self.parser.parse_args(flags + ["--"] + values)
        else:
            options = self.parser.parse_args(args)

        return subcommand_handlers[subcommand](options)
