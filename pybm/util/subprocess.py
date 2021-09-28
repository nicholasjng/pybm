from typing import List, Tuple, Optional
import subprocess


def run_subprocess(command: List[str],
                   reraise_on_error: bool = True,
                   print_status: bool = True,
                   stdout: Optional[int] = subprocess.PIPE,
                   stderr: Optional[int] = subprocess.PIPE,
                   cwd: str = None) -> Tuple[int, str]:
    p = subprocess.run(command,
                       stdout=stdout,
                       stderr=stderr,
                       encoding="utf-8",
                       cwd=cwd)
    rc = p.returncode
    if rc != 0:
        return rc, p.stderr
    else:
        return rc, p.stdout
        # msg = f"The command `{full_command}` returned the non-zero " \
        #       f"exit code {rc}.\nFurther information (stderr " \
        #       f"output of the subprocess):\n{p.stderr}"
        # if print_status:
        #     print("failed.")
        #     if not reraise_on_error:
        #         print(msg)
        # if reraise_on_error:
        #     raise PybmError(msg)
    # return rc, p.stdout
