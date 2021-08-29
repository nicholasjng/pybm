import re
import subprocess
from typing import List, Text

from pybm.exceptions import ArgumentError, PybmError

_venv_options = ["--system-site-packages", "--symlinks", "--copies",
                 "--clear", "--upgrade", "--without-pip", "--upgrade-deps"]


def split_option_string(option_string: str) -> List[Text]:
    # Check both comma- and space-separated options
    for sep in [" ", ","]:
        option_list = option_string.split(sep)
        if all(opt in _venv_options for opt in option_list):
            return option_list
        else:
            continue

    eligible_options = ", ".join(_venv_options)
    msg = f"Failed parsing option string {option_string}. One or more " \
          f"arguments were not recognized as command line options for " \
          f"venv. Eligible options are: {eligible_options}"
    raise ArgumentError(msg)


def get_python_version(executable: str) -> Text:
    try:
        output = subprocess.check_output(
            [executable, "--version"]).decode("utf-8")
    except subprocess.CalledProcessError as e:
        raise ArgumentError(str(e))

    version_string = re.search(r'([\d.]+)', output)
    if version_string is not None:
        version = version_string.group()
        return version
    else:
        msg = f"unable to get version from Python executable {executable}."
        raise PybmError(msg)
