import subprocess
from pathlib import Path
from typing import List, Tuple, Union, Literal

from pybm.exceptions import PybmError

Handling = Literal["raise", "ignore"]


def run_subprocess(command: List[str],
                   allowed_statuscodes: List[int] = None,
                   ex_type: type = PybmError,
                   errors: Handling = "raise",
                   cwd: Union[str, Path] = None) -> Tuple[int, str]:
    full_command = " ".join(command)
    allowed_statuscodes = allowed_statuscodes or []
    allowed_statuscodes.append(0)
    # logger.debug(f"Running command {full_command}...")
    p = subprocess.run(command,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       encoding="utf-8",
                       cwd=cwd)
    rc = p.returncode
    if rc not in allowed_statuscodes:
        if errors == "raise":
            msg = f"The command `{full_command}` returned the non-zero " \
                  f"exit code {rc}.\nFurther information (stderr " \
                  f"output of the subprocess):\n{p.stderr}"
            raise ex_type(msg)
        else:
            return rc, p.stderr
    return rc, p.stdout
