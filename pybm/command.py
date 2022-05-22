import argparse
import os
import sys
from typing import List

from pybm.exceptions import GitError, PybmError
from pybm.statuscodes import ERROR


class CustomFormatter(argparse.RawDescriptionHelpFormatter):
    def _format_action_invocation(self, action):
        if not action.option_strings:
            (metavar,) = self._metavar_formatter(action, action.dest)(1)
            return metavar
        else:
            parts = []
            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                parts.extend(action.option_strings)
                parts[-1] += f" {args_string}"
            return ", ".join(parts)


class CLICommand:
    """CLI command base class."""

    usage = ""

    def __init__(self, name: str = "", **parser_kwargs):
        # command name
        self.name = name
        self.parser = argparse.ArgumentParser(
            add_help=False,
            prog=self.format_name(),
            usage=self.usage,
            description=self.__doc__,
            formatter_class=CustomFormatter,
            **parser_kwargs,
        )

        self.parser.add_argument(
            self.parser.prefix_chars + "h",
            self.parser.prefix_chars * 2 + "help",
            action="help",
            default=argparse.SUPPRESS,
            help="Show this message and exit.",
        )

        self.parser.add_argument(
            self.parser.prefix_chars + "v",
            action="store_true",
            default=False,
            dest="verbose",
            help="Enable verbose mode. Makes pybm "
            "log information that might be useful "
            "for debugging.",
        )

    def add_arguments(self):
        """Add arguments to class argument parser member."""
        raise NotImplementedError

    def format_name(self) -> str:
        return f"pybm {self.name}".strip()

    def format_call(self, args: List[str]) -> str:
        return self.format_name() + " " + " ".join(args)

    def run_wrapped(self, args: List[str]):
        try:
            return self.run(args)
        except (PybmError, GitError) as e:
            sys.stderr.write(f"Error: {e}")
            sys.stderr.write(os.linesep)
            sys.exit(ERROR)

    def run(self, args: List[str]) -> int:
        """Execute the logic behind a run CLI command."""
        raise NotImplementedError
