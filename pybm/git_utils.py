import os
from typing import List, Iterable, Tuple
from pathlib import Path

# small git flag database for worktree commands
from pybm.exceptions import GitError

_git_worktree_flags = {
    "add": {"force": {True: "-f", False: None},
            "checkout": {True: "--checkout", False: "--no-checkout"},
            "lock": {True: "--lock", False: None},
            },
    "list": {"porcelain": {True: "--porcelain", False: None}},
    "remove": {"force": {True: "-f", False: None}}
}


def lmap(fn, iterable: Iterable):
    return list(map(fn, iterable))


def tmap(fn, iterable: Iterable):
    return tuple(map(fn, iterable))


def is_git_repository():
    # Check relative to current path, assumes everything is working.
    return os.path.exists(".git")


def get_repository_name():
    return Path.cwd().stem


def git_feature_guard(command_name: str, min_version: Tuple[int],
                      installed: Tuple[int]):
    def version_string(x):
        return ".".join(map(str, x))
    if installed < min_version:
        raise GitError(f"The `git {command_name}` command was first added in "
                       f"git version {version_string(min_version)}, but your "
                       f"git version is {version_string(installed)}.")


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
