import re
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Union

from pybm.exceptions import GitError
from pybm.util.common import lmap, lfilter, version_tuple


def run_subprocess(command: List[str],
                   reraise_on_err: bool = True,
                   cwd: Union[str, Path, None] = None) -> Tuple[int, str]:
    p = subprocess.run(command,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       encoding="utf-8",
                       cwd=cwd)
    rc = p.returncode
    if rc != 0 and reraise_on_err:
        full_command = " ".join(command)
        msg = f"The command `{full_command}` returned the non-zero " \
              f"exit code {rc}.\nFurther information (stderr " \
              f"output of the subprocess):\n{p.stderr}"
        raise GitError(msg)
    return rc, p.stdout


def is_git_repository(path: Union[str, Path]) -> bool:
    # https://stackoverflow.com/questions/2180270/check-if-current-directory-is-a-git-repository
    cmd = ["git", "rev-parse", "--is-inside-work-tree"]
    # command raises if not inside a worktree
    rc, msg = run_subprocess(cmd, False, cwd=path)
    return rc == 0


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
        msg = f"Input {commit_ish!r} did not resolve to any known local " \
              f"branch, tag or valid commit SHA1."
        raise GitError(msg)
    # force commit resolution, leads to detached HEAD
    if resolve_commits:
        ref, ref_type = resolve_commit(ref), "commit"
    return ref, ref_type


def list_tags():
    rc, tags = run_subprocess(["git", "tag"])
    return tags.splitlines()


def map_commits_to_tags() -> Dict[str, str]:
    """Return key-value mapping commit -> tag name"""

    # -d switch shows commit SHA1s pointed to by tag, marked by `^{}`
    # https://stackoverflow.com/questions/8796522/git-tag-list-display-commit-sha1-hashes
    def process_line(line: str) -> Tuple[str, str]:
        commit, tag = line.rstrip(tag_marker).split()
        return commit, tag

    tag_marker = "^{}"
    # show-ref exits with 1 if no tags exist in the repo
    rc, tags = run_subprocess(["git", "show-ref", "--tags", "-d"],
                              reraise_on_err=False)
    commits_and_tags = lfilter(lambda x: x.endswith(tag_marker), tags)
    # closure above is required here to keep mypy happy
    split_list = lmap(process_line, commits_and_tags)
    return dict(split_list)


def list_local_branches():
    rc, branches = run_subprocess(["git", "branch"])
    # strip leading formatting tokens from git branch output
    return lmap(lambda x: x.lstrip(" *+"), branches.splitlines())


def get_git_version() -> Tuple[int, ...]:
    rc, output = run_subprocess(["git", "--version"])
    version_string = re.search(r'([\d.]+)', output)
    if version_string is not None:
        version = version_string.group()
        return version_tuple(version)
    else:
        raise GitError("Unable to get version from git.")


def resolve_commit(ref: str) -> str:
    if is_valid_sha1_part(ref):
        command = ["git", "rev-parse", ref]
    else:
        command = ["git", "rev-list", "-n", "1", ref]
    _, commit = run_subprocess(command)
    return commit


def disambiguate_info(info: str) -> str:
    if Path(info).exists() and is_git_repository(info):
        attr = "root"
    elif is_valid_sha1_part(info):
        attr = "commit"
    elif info in list_local_branches():
        attr = "branch"
    elif info in list_tags():
        attr = "tag"
    else:
        # TODO: Display close matches if present
        msg = f"Argument {info!r} was not recognized as an attribute of an " \
              f"existing environment worktree."
        raise GitError(msg)
    return attr
