import argparse
import contextlib
from dataclasses import asdict, is_dataclass
from typing import List, Optional, Mapping, Callable

import toml

from pybm.command import CLICommand
from pybm.config import PybmConfig
from pybm.exceptions import PybmError
from pybm.status_codes import ERROR, SUCCESS
from pybm.util.common import lpartition

EnvSubcommand = Callable[[argparse.Namespace], int]


class ConfigCommand(CLICommand):
    """Display and manipulate configuration values."""

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
        if subcommand == "get":
            self.parser.add_argument(
                "option",
                type=str,
                metavar="<option>",
                help="Config option to display. For a comprehensive list of options, "
                "run `pybm config list`.",
            )
        elif subcommand == "set":
            self.parser.add_argument(
                "option",
                type=str,
                metavar="<option>",
                help="Config option to set. For a comprehensive list of options, "
                "run `pybm config list`.",
            )
            # TODO: Revise nargs value for this option
            self.parser.add_argument(
                "value",
                metavar="<value>",
                help="New value to set for the chosen config option.",
            )
        elif subcommand == "describe":
            self.parser.add_argument(
                "option",
                type=str,
                metavar="<option>",
                help="Config option to describe. For a comprehensive list of options, "
                "run `pybm config list`.",
            )

    @contextlib.contextmanager
    def context(self, op: str, attr: str, value: Optional[str], verbose: bool = False):
        # TODO: This is BS
        is_group = "." not in attr
        expr = "value" + "s" * is_group + f" {value!r}" * (value is not None)
        try:
            if verbose:
                opt_type = "group" if is_group else "option"
                op = op.capitalize()
                print(f"{op}ting {expr} for config {opt_type} {attr!r}.....", end="")
            yield
            if verbose:
                print("done.")
        except PybmError as e:
            if verbose:
                print("failed.")
            raise e

    def get(self, options: argparse.Namespace) -> int:
        verbose: bool = options.verbose
        attr: str = options.option

        with self.context("get", attr, None, verbose):
            value = PybmConfig.load().get_value(attr)

        if is_dataclass(value):
            print(toml.dumps({attr: asdict(value)}))
        else:
            print(f"{attr} = {value}")

        return SUCCESS

    def set(self, options: argparse.Namespace) -> int:
        verbose: bool = options.verbose

        attr, value = str(options.option), str(options.value)

        with self.context("set", attr, value, verbose):
            PybmConfig.load().set_value(attr, value).save()

        return SUCCESS

    @staticmethod
    def list(options: argparse.Namespace) -> int:
        config = PybmConfig.load(".pybm/config.toml")

        print(config.to_string())

        return SUCCESS

    @staticmethod
    def describe(options: argparse.Namespace) -> int:
        attr: str = options.option

        if attr.startswith("_"):
            raise PybmError(
                "Private configuration attributes cannot "
                "be described via `pybm config describe`."
            )

        PybmConfig.load().describe(attr)

        return SUCCESS

    def run(self, args: List[str]):
        subcommand_handlers: Mapping[str, EnvSubcommand] = {
            "set": self.set,
            "get": self.get,
            "list": self.list,
            "describe": self.describe,
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
            flag_names = ["-h", "--help", "-v"]
            flags, values = lpartition(lambda x: x in flag_names, args)
            options = self.parser.parse_args(flags + ["--"] + values)
        else:
            options = self.parser.parse_args(args)

        return subcommand_handlers[subcommand](options)
