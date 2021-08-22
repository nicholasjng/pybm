import subprocess
from typing import Dict, List, Union


class CommandWrapperMixin:
    """Useful utilities for CLI command wrappers such as git, venv etc."""

    def __init__(self, command_db: Dict, exception_type: type):
        self.command_db = command_db
        self.exception_type = exception_type

    def parse_flags(self, command: str, **kwargs):
        flags = []
        for k, v in kwargs.items():
            command_options = self.command_db[command]
            if k not in command_options:
                # TODO: log bad kwarg usage somewhere
                continue
            cmd_opts = command_options[k]
            if v not in cmd_opts:
                raise ValueError(f"unknown value {v} given for option {k}.")
            flag = cmd_opts[v]
            if flag is not None:
                flags.append(flag)
        return flags

    def wrapped_subprocess_call(self, name: str, call_args: List[str],
                                **subprocess_kwargs) -> Union[int, str]:
        sp_api = getattr(subprocess, name)
        try:
            return sp_api(call_args, **subprocess_kwargs)
        except subprocess.CalledProcessError as e:
            full_command = " ".join(call_args)
            msg = f"The command `{full_command}` returned the non-zero " \
                  f"exit code {e.returncode}.\nFurther information (" \
                  f"output of the subprocess command):\n{e.output}"
            raise self.exception_type(msg)
