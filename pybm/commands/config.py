import argparse
import contextlib
from dataclasses import asdict, is_dataclass
from typing import List, Optional

from pybm.command import CLICommand
from pybm.config import PybmConfig, get_all_names
from pybm.exceptions import PybmError
from pybm.status_codes import ERROR, SUCCESS
from pybm.util.common import lpartition


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
                help="Config option to display. For a "
                "comprehensive list of options, "
                "run `pybm config list`.",
            )
        elif subcommand == "set":
            self.parser.add_argument(
                "option",
                type=str,
                metavar="<option>",
                help="Config option to set. For a "
                "comprehensive list of options, "
                "run `pybm config list`.",
            )
            # TODO: Revise nargs value for this option
            self.parser.add_argument(
                "value",
                metavar="<value>",
                help="Config option to display. For a "
                "comprehensive list of options, "
                "run `pybm config list`.",
            )
        elif subcommand == "describe":
            self.parser.add_argument(
                "option",
                type=str,
                metavar="<option>",
                help="Config option to describe. For a "
                "comprehensive list of options, "
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

    def get(self, options: argparse.Namespace, verbose: bool) -> int:
        attr: str = options.option

        with self.context("get", attr, None, verbose):
            value = PybmConfig.load(".pybm/config.yaml").get_value(attr)

        if is_dataclass(value):
            for k, v in asdict(value).items():
                print(f"{k} = {v}")
        else:
            print(f"{attr} = {value}")

        return SUCCESS

    def set(self, options: argparse.Namespace, verbose: bool) -> int:
        attr, value = options.option, options.value
        path = ".pybm/config.yaml"

        with self.context("set", attr, value, verbose):
            PybmConfig.load(path).set_value(attr, value).save(path)

        return SUCCESS

    @staticmethod
    def list(options: argparse.Namespace, verbose: bool) -> int:
        del verbose  # unused
        config = PybmConfig.load(".pybm/config.yaml")

        for name in get_all_names(config):
            group = config.get_value(name)
            print(f"Config values for group {name!r}:")

            for k, v in asdict(group).items():
                val = v if v != "" else "(empty string)"
                print(f"{k} : {val}")

            print("")
        return SUCCESS

    @staticmethod
    def describe(options: argparse.Namespace, verbose: bool) -> int:
        del verbose  # unused
        attr = options.option

        if "__" in attr:
            raise PybmError(
                "Only unprivileged configuration attributes can "
                "be described via `pybm config describe`."
            )

        config = PybmConfig.load(".pybm/config.yaml")
        config.describe(attr)

        return SUCCESS

    def run(self, args: List[str]):
        subcommand_handlers = {
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
        # optional arguments (e.g. for venv flags)
        # https://docs.python.org/3/library/argparse.html#arguments-containing
        if subcommand == "set":
            # Insert the double hyphen after flags, otherwise they break
            flag_names = ["-h", "--help", "-v"]
            flags, values = lpartition(lambda x: x in flag_names, args)
            options = self.parser.parse_args(flags + ["--"] + values)
        else:
            options = self.parser.parse_args(args)

        verbose: bool = options.verbose

        return subcommand_handlers[subcommand](options, verbose)
