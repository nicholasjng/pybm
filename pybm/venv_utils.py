from typing import List

_virtualenv_flags = {
    "overwrite": {True: "--clear", False: None}
}

def parse_venv_flags(**kwargs) -> List[str]:
    venv_flags = []
    for k, v in kwargs.items():
        if k not in _virtualenv_flags:
            raise ValueError(f"unknown option {k} supplied.")
        options = _virtualenv_flags[k]
        if v not in options:
            raise ValueError(f"unknown value {v} given for option {k}.")
        flag = options[v]
        if flag is not None:
            venv_flags.append(flag)
    return venv_flags
