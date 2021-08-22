import argparse
import sys
from typing import Any, List

from pybm.exceptions import ArgumentError, GitError, VenvError, \
    write_exception_info


class CLICommand:
    """CLI command base class."""
    usage = None

    def __init__(self, name: str, **parser_kwargs):
        # command name
        self.name = name
        self.parser = argparse.ArgumentParser(
            prog=self.format_name(),
            usage=self.usage,
            description=self.__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            **parser_kwargs
        )
        self.parser.add_argument("-v",
                                 action="count",
                                 default=0,
                                 help="Enable verbose mode. Makes pybm "
                                      "log information that might be useful "
                                      "for debugging.")

    def add_arguments(self):
        """Add arguments to class argument parser member."""
        raise NotImplementedError

    def format_name(self) -> str:
        return f"pybm {self.name}".strip()

    def run_wrapped(self, args: List[Any]):
        try:
            return self.run(args)
        except (
                ArgumentError,
                NotImplementedError
        ) as e:
            write_exception_info(e)
        except GitError as e:
            write_exception_info(e, origin="git")
        except VenvError as e:
            write_exception_info(e, origin="venv")
        finally:
            sys.exit(1)

    def run(self, args: List[Any]) -> int:
        """Execute the logic behind a run CLI command."""
        raise NotImplementedError
