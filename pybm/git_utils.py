import os
import re
import subprocess
from typing import List, Iterable, Tuple
from pathlib import Path

from pybm.exceptions import GitError, ArgumentError

MIN_VERSION = "min_version"
OPTIONS = "options"

_git_feature_versions = {
    "add": {
        MIN_VERSION: (2, 6, 7),
        OPTIONS: {
            "-f": (2, 6, 7),
            "--checkout": (2, 9, 5),
            "--no-checkout": (2, 9, 5),
            "--lock": (2, 13, 7),
        },
    },
    "list": {
        MIN_VERSION: (2, 7, 6),
        OPTIONS: {
            "--porcelain": (2, 7, 6),
        },
    },
    "remove": {
        MIN_VERSION: (2, 17, 0),
        OPTIONS: {
            "-f": (2, 17, 0),
        },
    },
}


def lmap(fn, iterable: Iterable):
    return list(map(fn, iterable))


def tmap(fn, iterable: Iterable) -> Tuple:
    return tuple(map(fn, iterable))


def lfilter(fn, iterable: Iterable) -> List:
    return list(filter(fn, iterable))


def tfilter(fn, iterable: Iterable) -> Tuple:
    return tuple(filter(fn, iterable))


def is_git_repository(path: str):
    # Check relative to current path, assumes everything is working.
    # TODO: git worktrees contain a file called .git, does this still work?
    return os.path.exists(os.path.join(path, ".git"))


def get_repository_name():
    return Path.cwd().stem


def is_valid_sha1_part(input_str: str) -> bool:
    try:
        # valid SHA1s can be cast to a hex integer
        _ = int(input_str, 16)
    except ValueError:
        return False
    return True


def resolve_to_ref(commit_ish: str, resolve_commits: bool):
    ref = commit_ish
    if commit_ish in list_tags():
        # ref is a tag name
        ref_type = "tag"
    # TODO: Make a worktree from a remote branch (does not appear here)
    elif commit_ish in list_local_branches():
        # ref is a local branch name
        ref_type = "branch"
    elif is_valid_sha1_part(commit_ish):
        ref_type = "commit"
    else:
        msg = f"input {commit_ish} did not resolve to any known local " \
              f"branch, tag or commit SHA1. If you specified a commit SHA " \
              f"fragment, please make sure it is at least 7 characters long " \
              f"to ensure git SHA resolution works."
        raise GitError(msg)
    # force commit resolution, leads to detached HEAD
    if resolve_commits:
        ref, ref_type = resolve_commit(ref), "commit"

    return ref, ref_type


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


def get_git_version() -> Tuple[int]:
    try:
        output = subprocess.check_output(["git", "--version"]).decode("utf-8")
        version_string = re.search(r'([\d.]+)', output).group()
        return tmap(int, version_string.split("."))
    except subprocess.CalledProcessError as e:
        raise GitError(str(e))


def resolve_commit(ref: str) -> str:
    try:
        if is_valid_sha1_part(ref):
            return subprocess.check_output(
                ["git", "rev-parse", ref]).decode("utf-8")
        else:
            return subprocess.check_output(
                ["git", "rev-list", "-n", "1", ref]).decode("utf-8")
    except subprocess.CalledProcessError as e:
        raise GitError(str(e))


def disambiguate_info(info: str) -> str:
    if os.path.exists(info):
        attr = info
    elif is_valid_sha1_part(info):
        attr = "commit"
    elif info in list_local_branches():
        attr = "branch"
    elif info in list_tags():
        attr = "tag"
    else:
        # TODO: Display close matches if present
        msg = f"argument {info} was not recognized as an attribute of an " \
              f"existing environment worktree."
        raise ArgumentError(msg)

    return attr


def git_worktree_feature_guard(command: List[str]):
    def version_string(x):
        return ".".join(map(str, x))

    assert len(command) > 2 and command[:2] == ["git", "worktree"], \
        "internal git command construction error"

    worktree_command, rest = command[2], command[2:]
    assert worktree_command in _git_feature_versions, f"unimplemented git " \
                                                      f"worktree command " \
                                                      f"`{worktree_command}`"

    command_data = _git_feature_versions[worktree_command]
    min_version, options = command_data[MIN_VERSION], command_data[OPTIONS]
    # log offending command or option for dynamic exception printing
    newest, dtype = worktree_command, "command"

    for k in lfilter(lambda x: x.startswith("-"), rest):
        if k in options:
            contender = options[k]
            if contender > min_version:
                min_version = contender
                newest, dtype = k, "option"

    installed = get_git_version()
    full_command = " ".join(command)

    if installed < min_version:
        raise GitError(f"Running the command `{full_command}` requires a "
                       f"minimum git version of"
                       f"{version_string(min_version)}, but your git "
                       f"version was found to be only"
                       f" {version_string(installed)}. "
                       f"This version requirement is because the {dtype} "
                       f"`{newest}` was used, which was first introduced in "
                       f"git version {version_string(min_version)}.")
