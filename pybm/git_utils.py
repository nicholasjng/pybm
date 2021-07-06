import os
from typing import List

_git_worktree_flags = {
    "add": {"force": {True: "-f", False: None},
            "checkout": {True: "--checkout", False: "--no-checkout"},
            "lock": {True: "--lock", False: None},
            },
    "list": {"porcelain": {True: "--porcelain", False: None}},
    "remove": {"force": {True: "-f", False: None}}
}

def is_git_repository():
    # Check relative to current path, assumes everything is working.
    return os.path.exists(".git")

def parse_flags(command: str, subcommand: str, **kwargs) -> List[str]:
    if command != "worktree":
        raise NotImplementedError("git flag parsing is only available for "
                                  "worktree right now.")
    git_flags = []
    # TODO: Improve this logic for commands without subcommands
    for k, v in kwargs.items():
        subcommand_options = _git_worktree_flags[subcommand]
        if k not in subcommand_options:
            # TODO: log bad kwarg usage somewhere
            continue
        if v not in subcommand_options[k]:
            raise ValueError(f"unknown value {v} given for option {k}.")
        flag = subcommand_options[k][v]
        if flag is not None:
            git_flags.append(flag)

    return git_flags
