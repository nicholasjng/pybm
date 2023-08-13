import re
import typing
from functools import lru_cache, partial
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

if typing.TYPE_CHECKING:
    # Literal exists only from Python 3.8 onwards
    # solution source:
    # https://github.com/pypa/pip/blob/main/src/pip/_internal/utils/subprocess.py
    from typing import Literal

from pybm.exceptions import GitError, PybmError
from pybm.util.common import lfilter, lmap, version_string, version_tuple
from pybm.util.subprocess import run_subprocess

git_subprocess = partial(run_subprocess, ex_type=GitError)


def _feature_guard(command: str, min_git: Tuple[int, int, int]):
    if GIT_VERSION < min_git:
        msg = (
            f"The command `git {command}` requires at minimum git version "
            f"{version_string(min_git)}, "
        )

        if GIT_VERSION == (0, 0, 0):
            msg += (
                "but no git installation was found on your system. Please ensure "
                "that git is installed and available on your PATH."
            )
        else:
            msg += f"but your installed git is only version {version_string(GIT_VERSION)}."
        raise PybmError(msg)


def checkout(ref: Optional[str], cwd: Union[str, Path]) -> None:
    command = ["git", "checkout"]
    if ref is not None:
        command.append(ref)

    git_subprocess(command=command, cwd=cwd)


def cherrypick(commits: Union[str, typing.Sequence[str]], cwd: Union[str, Path]) -> None:
    if isinstance(commits, str):
        commits = (commits,)

    command = ["git", "cherry-pick", *commits, "--strategy-option=theirs"]

    git_subprocess(command, cwd=cwd)


def disambiguate(ref: str) -> Optional[str]:
    ref_type: Optional[str] = None
    if is_valid_sha_part(ref):
        ref_type = "commit"
    elif ref in list_branches(mode="all", names_only=True):
        # check for branch name, remote or local
        ref_type = "branch"
    elif ref in list_tags():
        ref_type = "tag"
    return ref_type


def get_from_history(
    ref: str,
    resource: str,
    directory: Union[str, Path],
) -> None:
    """Check out a file or directory from another reference in the git history."""
    with_checkout = GIT_VERSION < (2, 23, 0)

    if with_checkout:
        # git <2.23: checkouts from other branches are moved to the staging area
        command = ["git", "checkout", ref, "--", resource]
    else:
        # https://stackoverflow.com/questions/307579/how-do-i-copy-a-version-of-a-single-file-from-one-git-branch-to-another
        command = ["git", "restore", "--source", ref, resource]

    # errors here (e.g. nonexistent resource) are immediately raised
    git_subprocess(command=command, cwd=directory)

    if with_checkout:
        # remove checked out resource from staging area
        git_subprocess(["git", "reset", "HEAD", "--", resource])


def get_git_version() -> Tuple[int, int, int]:
    rc, output = git_subprocess(["git", "--version"])

    version_str = re.search(r"\d+(\.\d+)+", output)
    if version_str is not None:
        return version_tuple(version_str.group())
    else:
        raise GitError("Unable to get version from git.")


# Current git version
# ---------------------------------------
try:
    GIT_VERSION = get_git_version()
except GitError:
    GIT_VERSION = (0, 0, 0)
# ---------------------------------------


def is_git_worktree(path: Union[str, Path]) -> bool:
    # https://stackoverflow.com/questions/2180270/check-if-current-directory-is-a-git-repository
    cmd = ["git", "rev-parse", "--is-inside-work-tree"]
    # command exits with 128 if not inside a worktree
    rc, _ = git_subprocess(cmd, allowed_statuscodes=[128], cwd=path)
    return rc == 0


def is_main_worktree(path: Union[str, Path]) -> bool:
    git_path = Path(path) / ".git"
    return git_path.is_dir() and is_git_worktree(path)


def is_valid_sha_part(s: str) -> bool:
    # SHA256 occupy exactly 64 hexs, anything less or equal is fine
    if len(s) > 64:
        return False
    try:
        # valid SHA256s can be cast to a hex integer
        int(s, 16)
    except ValueError:
        return False
    return True


def list_branches(
    mode: 'Literal["local", "remote", "all"]' = "all", names_only: bool = False
) -> List[str]:
    command = ["git", "branch"]

    if mode == "all":
        command += ["-a"]
    elif mode == "remote":
        # TODO: Select remote out of multiple
        command += ["-r"]

    # name-only listing with the "format" option to `git branch`
    command += ["--format=%(refname:short)"]

    # every line is a branch name
    rc, branch_output = git_subprocess(command)

    branches: List[str] = branch_output.splitlines()

    if names_only:
        # only split off the remote name by maxsplit=1
        branches = list(set([b.split("/", maxsplit=1)[-1] for b in branches]))

    return branches


def list_tags() -> List[str]:
    # every line is a tag name
    rc, tags = git_subprocess(["git", "tag"])

    return tags.splitlines()


def main_worktree_directory() -> Path:
    # this gives the absolute location of the main git folder
    command = ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"]
    rc, output = git_subprocess(command, cwd=Path.cwd())
    # ergo, parent folder is the target directory
    return Path(output.rstrip()).parent


@lru_cache
def map_commits_to_tags() -> Dict[str, str]:
    """Return key-value mapping (commit) -> (tag name)."""
    tag_marker = "^{}"

    def process_line(line: str) -> Tuple[str, str]:
        commit, tag = line.rstrip(tag_marker).split()
        tag = tag.replace("refs/tags/", "")
        return commit, tag

    # show-ref exits with 1 if no tags exist in the repo
    # -d switch shows commit SHA1s pointed to by tag, marked by `^{}`
    # https://stackoverflow.com/questions/8796522/git-tag-list-display-commit-sha1-hashes
    rc, tags = git_subprocess(["git", "show-ref", "--tags", "-d"], allowed_statuscodes=[1])
    commits_and_tags = lfilter(lambda x: x.endswith(tag_marker), tags.splitlines())
    # closure above is required here to keep mypy happy
    split_list = lmap(process_line, commits_and_tags)
    return dict(split_list)


def repository_name() -> str:
    return main_worktree_directory().name


def resolve_commit(ref: str) -> str:
    if is_valid_sha_part(ref):
        command = ["git", "rev-parse", ref]
    else:
        # for getting the actual commit instead of the tag SHA
        command = ["git", "rev-list", "-n", "1", ref]

    _, commit = git_subprocess(command)
    # rev-parse branch output is newline-terminated
    return commit.rstrip()


def resolve_ref(ref: str, resolve_commits: bool) -> Tuple[str, str]:
    if ref in list_tags():
        ref_type = "tag"
    elif ref in list_branches(mode="all", names_only=True):
        # ref is a branch name
        ref_type = "branch"
    elif is_valid_sha_part(ref):
        ref_type = "commit"
    else:
        raise GitError(f"Input {ref!r} did not resolve to any known branch, tag, or commit SHA.")
    # force commit resolution, leads to detached HEAD
    if resolve_commits:
        ref, ref_type = resolve_commit(ref), "commit"
    return ref, ref_type
