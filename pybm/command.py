import argparse
import os
import sys
from typing import List

from pybm.exceptions import GitError, BuilderError, PybmError
from pybm.status_codes import ERROR


class CLICommand:
    """CLI command base class."""

    usage = ""

    def __init__(self, name: str, **parser_kwargs):
        # command name
        self.name = name
        self.parser = argparse.ArgumentParser(
            add_help=False,
            prog=self.format_name(),
            usage=self.usage,
            description=self.__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter,
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
        except (PybmError, GitError, BuilderError) as e:
            sys.stderr.write(f"Error: {e}")
            sys.stderr.write(os.linesep)
            sys.exit(ERROR)

    def run(self, args: List[str]) -> int:
        """Execute the logic behind a run CLI command."""
        raise NotImplementedError
