import os
import re
import subprocess
from typing import List, Iterable, Tuple, Callable, TypeVar, Any

from pybm.exceptions import GitError, ArgumentError

T = TypeVar('T')
S = TypeVar('S')


def lmap(fn: Callable[[S], T], iterable: Iterable[S]) -> List[T]:
    return list(map(fn, iterable))


def tmap(fn: Callable[[S], T], iterable: Iterable[S]) -> Tuple[T, ...]:
    return tuple(map(fn, iterable))


def lfilter(fn: Callable[[S], Any], iterable: Iterable[S]) -> List[S]:
    return list(filter(fn, iterable))


def tfilter(fn: Callable[[S], Any], iterable: Iterable[S]) -> Tuple[S, ...]:
    return tuple(filter(fn, iterable))


def run_subprocess(command: List[str]) -> Tuple[int, str]:
    p = subprocess.run(command,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       encoding="utf-8")
    rc = p.returncode
    if rc != 0:
        full_command = " ".join(command)
        msg = f"The command `{full_command}` returned the non-zero " \
              f"exit code {rc}.\nFurther information (stderr " \
              f"output of the subprocess):\n{p.stderr}"
        raise GitError(msg)

    return rc, p.stdout


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
              f"branch, tag or valid commit SHA1."
        raise ArgumentError(msg)
    # force commit resolution, leads to detached HEAD
    if resolve_commits:
        ref, ref_type = resolve_commit(ref), "commit"

    return ref, ref_type


def list_tags():
    rc, tags = run_subprocess(["git", "tag"])
    return tags.splitlines()


def list_local_branches():
    rc, branches = run_subprocess(["git", "branch"])
    # strip leading formatting tokens from git branch output
    return lmap(lambda x: x.lstrip(" *+"), branches.splitlines())


def get_git_version() -> Tuple[int, ...]:
    rc, output = run_subprocess(["git", "--version"])
    version_string = re.search(r'([\d.]+)', output)
    if version_string is not None:
        version = version_string.group()
        return tmap(int, version.split("."))
    else:
        raise GitError("unable to get version from git.")


def resolve_commit(ref: str) -> str:
    if is_valid_sha1_part(ref):
        command = ["git", "rev-parse", ref]
    else:
        command = ["git", "rev-list", "-n", "1", ref]

    _, commit = run_subprocess(command)
    return commit


def disambiguate_info(info: str) -> str:
    if os.path.exists(info):
        attr = "worktree"
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
