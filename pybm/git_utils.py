import os
import re
import subprocess
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


def tmap(fn, iterable: Iterable) -> Tuple:
    return tuple(map(fn, iterable))


def lfilter(fn, iterable: Iterable) -> List:
    return list(filter(fn, iterable))


def tfilter(fn, iterable: Iterable) -> Tuple:
    return tuple(filter(fn, iterable))


def is_git_repository():
    # Check relative to current path, assumes everything is working.
    return os.path.exists(".git")


def get_repository_name():
    return Path.cwd().stem


def list_tags():
    try:
        tags = subprocess.check_output(["git", "tag"]).decode("utf-8")
        return tags.splitlines()
    except subprocess.CalledProcessError as e:
        raise GitError(str(e))


def list_local_branches():
    try:
        branches = subprocess.check_output(["git", "branch"]).decode("utf-8")
        # strip leading formatting tokens from git branch output
        return lmap(lambda x: x.lstrip(" *+"), branches.splitlines())
    except subprocess.CalledProcessError as e:
        raise GitError(str(e))


def get_version() -> Tuple[int]:
    try:
        output = subprocess.check_output(["git", "--version"]).decode("utf-8")
        version_string = re.search(r'([\d.]+)', output).group()
        return tmap(int, version_string.split("."))
    except subprocess.CalledProcessError as e:
        raise GitError(str(e))


def resolve_commit(ref: str, ref_type: str = "branch") -> str:
    if ref_type not in ["branch", "tag"]:
        raise GitError(f"unknown ref type {ref_type} encountered in "
                       f"git reference resolution attempt.")

    resolved_ref = f"tags/{ref}" if ref_type == "tag" else f"refs/heads/{ref}"
    try:
        return subprocess.check_output(["git", "rev-list", "-n", "1",
                                        resolved_ref]).decode("utf-8")
    except subprocess.CalledProcessError as e:
        raise GitError(str(e))


def git_feature_guard(command_name: str, min_version: Tuple[int],
                      installed: Tuple[int]):
    def version_string(x):
        return ".".join(map(str, x))
    if installed < min_version:
        raise GitError(f"The `git {command_name}` command was first added in "
                       f"git version {version_string(min_version)}, but your "
                       f"git version is {version_string(installed)}.")


def parse_flags(command: str, **kwargs) -> List[str]:
    flags = []
    for k, v in kwargs.items():
        command_options = _git_worktree_flags[command]
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
