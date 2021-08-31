import subprocess
from typing import List, Tuple, Text


class CommandWrapperMixin:
    """Useful utilities for CLI command wrappers such as git, venv etc."""

    def __init__(self, exception_type: type):
        self.exception_type = exception_type

    def raise_on_error(self, command: List[Text], ret_code: int, stderr: str):
        full_command = " ".join(command)
        msg = f"The command `{full_command}` returned the non-zero " \
              f"exit code {ret_code}.\nFurther information (stderr " \
              f"output of the subprocess):\n{stderr}"
        raise self.exception_type(msg)

    def run_subprocess(self, command: List[str], **subprocess_kwargs) \
            -> Tuple[int, str]:
        p = subprocess.run(command,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           encoding="utf-8",
                           **subprocess_kwargs)
        rc = p.returncode
        if rc != 0:
            self.raise_on_error(command, rc, stderr=p.stderr)

        return rc, p.stdout
