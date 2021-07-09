import argparse
from typing import List, Any
from pybm.parsers import get_command_parser

class CLICommand:
    """CLI command base class."""
    def __init__(self, name: str):
        self.name = name
        self.parser: argparse.ArgumentParser = get_command_parser(name)

    def parse_args(self, args: Any):
        return self.parser.parse_args(args)

    def run(self, *args, **kwargs):
        raise NotImplementedError


class VersionCommand(CLICommand):
    def run(self, *args, **kwargs):
        pass
