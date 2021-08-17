import os
import re
import subprocess
from typing import List, Iterable, Tuple
from pathlib import Path

# small git flag database for worktree commands
from pybm.exceptions import GitError


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


def is_valid_sha1_part(input_str: str, min_length: int = 7) -> bool:
    # enforce a minimum length to help git resolve SHA1s, default is 7
    if len(input_str) < min_length:
        return False
    else:
        try:
            # valid SHA1s can be cast to a hex integer
            _ = int(input_str, 16)
        except ValueError:
            return False
        return True


def resolve_to_ref(commit_ish: str, resolve_commits: bool):
    if commit_ish in list_tags():
        # ref is a tag name
        ref, ref_type = f"refs/tags/{commit_ish}", "tag"
    # TODO: Make a worktree from a remote branch (does not appear here)
    elif commit_ish in list_local_branches():
        # ref is a local branch name
        ref, ref_type = f"refs/heads/{commit_ish}", "branch"
    elif is_valid_sha1_part(commit_ish):
        ref, ref_type = commit_ish, "commit"
    else:
        msg = f"input {commit_ish} did not resolve to any known local " \
              f"branch, tag or commit SHA1."
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


def get_version() -> Tuple[int]:
    try:
        output = subprocess.check_output(["git", "--version"]).decode("utf-8")
        version_string = re.search(r'([\d.]+)', output).group()
        return tmap(int, version_string.split("."))
    except subprocess.CalledProcessError as e:
        raise GitError(str(e))


def resolve_commit(ref: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-list", "-n", "1", ref]
        ).decode("utf-8")
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
