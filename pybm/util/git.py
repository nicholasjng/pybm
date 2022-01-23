import re
import typing
from functools import partial
from pathlib import Path
from typing import Tuple, Dict, Union, Optional

if typing.TYPE_CHECKING:
    # Literal exists only from Python 3.8 onwards
    # solution source:
    # https://github.com/pypa/pip/blob/main/src/pip/_internal/utils/subprocess.py
    from typing import Literal

from pybm.exceptions import GitError
from pybm.util.common import lmap, lfilter, version_tuple, version_string
from pybm.util.subprocess import run_subprocess

git_subprocess = partial(run_subprocess, ex_type=GitError)


def get_git_version() -> Tuple[int, ...]:
    rc, output = git_subprocess(["git", "--version"])
    version_str = re.search(r"([\d.]+)", output)
    if version_str is not None:
        version = version_str.group()
        return version_tuple(version)
    else:
        raise GitError("Unable to get version from git.")


# ---------------------------------------
# Current git version
try:
    GIT_VERSION = get_git_version()
except GitError:
    GIT_VERSION = (0, 0, 0)


# ---------------------------------------


def _feature_guard(min_git: Tuple[int, int, int]):
    if GIT_VERSION < min_git:
        min_git_str = version_string(min_git)
        msg = f"Command `git restore` requires at minimum git version {min_git_str}, "

        if GIT_VERSION == (0, 0, 0):
            msg += (
                "but no git installation was found on your system. "
                "Please assure that git is installed and added to PATH."
            )
        else:
            curr_git_str = version_string(GIT_VERSION)
            msg += (
                f"but your installed git was found to be only version {curr_git_str}."
            )
        raise GitError(msg)


def is_git_worktree(path: Union[str, Path]) -> bool:
    # https://stackoverflow.com/questions/2180270/check-if-current-directory-is-a-git-repository
    cmd = ["git", "rev-parse", "--is-inside-work-tree"]
    # command exits with 1 if not inside a worktree
    rc, _ = git_subprocess(cmd, allowed_statuscodes=[1], cwd=path)
    return rc == 0


def is_main_worktree(path: Union[str, Path]) -> bool:
    git_path = Path(path) / ".git"
    has_git_folder = git_path.exists() and git_path.is_dir()
    return is_git_worktree(path) and has_git_folder


def is_valid_sha1_part(input_str: str) -> bool:
    try:
        # valid SHA1s can be cast to a hex integer
        _ = int(input_str, 16)
    except ValueError:
        return False
    return True


def resolve_ref(commit_ish: str, resolve_commits: bool):
    ref = commit_ish
    if commit_ish in list_tags():
        ref_type = "tag"
    elif commit_ish in list_branches(mode="all"):
        # ref is a local branch name
        ref_type = "branch"
    elif is_valid_sha1_part(commit_ish):
        ref_type = "commit"
    else:
        msg = (
            f"Input {commit_ish!r} did not resolve to any known local "
            f"branch, tag or valid commit SHA1."
        )
        raise GitError(msg)
    # force commit resolution, leads to detached HEAD
    if resolve_commits:
        ref, ref_type = resolve_commit(ref), "commit"
    return ref, ref_type


def list_tags():
    rc, tags = git_subprocess(["git", "tag"])
    return tags.splitlines()


def map_commits_to_tags() -> Dict[str, str]:
    """Return key-value mapping commit -> tag name"""

    # -d switch shows commit SHA1s pointed to by tag, marked by `^{}`
    # https://stackoverflow.com/questions/8796522/git-tag-list-display-commit-sha1-hashes
    def process_line(line: str) -> Tuple[str, str]:
        commit, tag = line.rstrip(tag_marker).split()
        tag = tag.replace("refs/tags/", "")
        return commit, tag

    tag_marker = "^{}"
    # show-ref exits with 1 if no tags exist in the repo
    rc, tags = git_subprocess(
        ["git", "show-ref", "--tags", "-d"], allowed_statuscodes=[1]
    )
    commits_and_tags = lfilter(lambda x: x.endswith(tag_marker), tags.splitlines())
    # closure above is required here to keep mypy happy
    split_list = lmap(process_line, commits_and_tags)
    return dict(split_list)


def list_branches(mode: 'Literal["local", "remote", "all"]' = "all"):
    def format_branch(name: str):
        name = name.lstrip(" *+")
        return name.split("/", maxsplit=2)[-1]

    command = ["git", "branch"]
    if mode == "all":
        command += ["-a"]
    elif mode == "remote":
        # TODO: Select remote out of multiple
        command += ["-r"]

    rc, output = git_subprocess(command)
    branches = output.splitlines()

    if mode != "local":
        # filter remote HEAD tracker from output
        branches = lfilter(lambda x: "->" not in x, branches)
    # strip leading formatting tokens from git branch output
    return lmap(format_branch, branches)


def resolve_commit(ref: str) -> str:
    if is_valid_sha1_part(ref):
        command = ["git", "rev-parse", ref]
    else:
        command = ["git", "rev-list", "-n", "1", ref]
    _, commit = git_subprocess(command)
    return commit.rstrip()


def disambiguate_info(info: str) -> Optional[str]:
    attr: Optional[str] = None
    p, pp = Path(info), Path.cwd().parent / info
    # check if path is present in either cwd or parent
    if p.exists() and is_git_worktree(p):
        attr = "root"
    elif pp.exists() and is_git_worktree(pp):
        attr = "root"
    elif is_valid_sha1_part(info):
        attr = "commit"
    elif info in list_branches(mode="all"):
        attr = "branch"
    elif info in list_tags():
        attr = "tag"
    return attr


def checkout(ref: str, cwd: Union[str, Path]):
    command = ["git", "checkout", ref]
    git_subprocess(command=command, cwd=cwd)


def get_from_history(ref: str, resource: Union[str, Path], directory: Union[str, Path]):
    """Check out a file or directory from another git reference."""
    # Source:
    # https://stackoverflow.com/questions/307579/how-do-i-copy-a-version-of-a-single-file-from-one-git-branch-to-another
    command = ["git", "restore", "--source", ref, str(resource)]

    _feature_guard(min_git=(2, 23, 0))
    # errors caught here (e.g. nonexistent resource) are immediately raised
    git_subprocess(command=command, cwd=directory)
