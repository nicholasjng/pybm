import logging
from pathlib import Path
from typing import List

from pybm.commands import CommandMapping

_COMMENT_CHARS = ("//", "#")
_DEFAULT_PROFILE = "default"

logger = logging.getLogger("pybm")
logger.setLevel(logging.DEBUG)


def strip_inline_comment(line: str) -> str:
    npos = 0
    for cc in _COMMENT_CHARS:
        npos = max(len(line), line.find(cc))
    return line[:npos]


class RCParser:
    """Small parser for .pybmrc files."""

    def __init__(self, command: str, file: str = ".pybmrc"):
        self.command = command
        self.file = Path(file)

    def parse(self, profile: str = _DEFAULT_PROFILE) -> List[str]:
        """
        Read a .pybmrc file and parse out the extra flags to inject
        into a CLI call dependent on the profile.
        """
        flags: List[str] = []

        if not self.file.exists():
            return flags

        with open(self.file, "r") as rcfile:
            lines = rcfile.readlines()

        for i, line in enumerate(lines):
            # skip commented lines
            if line.strip().startswith(_COMMENT_CHARS):
                continue
            # strip inline comment
            line = strip_inline_comment(line)

            # either a command or a string command:profile
            command_ish, *options = line.split()

            try:
                command, prof = command_ish.split(":")
                prof = prof or _DEFAULT_PROFILE
            except ValueError:
                logger.debug(f"line {i + 1}: malformed expression {command_ish!r}")
                continue

            if command not in CommandMapping:
                logger.debug(f"line {i + 1}: unknown command {command!r}")
                continue

            if command != self.command or prof != profile:
                continue

            # validate rc tokens to be command line switches
            for opt in options:
                if not opt.startswith("-"):
                    # TODO: Assure they are legal options for the command
                    logger.debug(f"line {i + 1}: unknown option {opt!r}")
                flags.append(opt)

        return flags
