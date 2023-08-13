"""Small Git worktree wrapper for operating on a repository via Python."""
import contextlib
import logging
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, List, Optional, Sequence, Tuple, Union

from pybm.exceptions import GitError, PybmError
from pybm.git.util import checkout as git_checkout
from pybm.git.util import (
    cherrypick,
    disambiguate,
    get_from_history,
    is_main_worktree,
    main_worktree_directory,
    map_commits_to_tags,
    resolve_commit,
    resolve_ref,
)
from pybm.util.common import lmap
from pybm.util.path import abbrev_home
from pybm.util.subprocess import run_subprocess

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclass
class Worktree:
    """Implements the git worktree data model."""

    root: Path
    commit: str
    branch: Optional[str] = None
    tag: Optional[str] = None
    locked: bool = False
    prunable: bool = False

    def checkout(self, resource: str):
        resource, ref = resource.split("@")
        get_from_history(
            ref=ref,
            resource=resource,
            directory=self.root,
        )

    def cherrypick(self, commits: Sequence[str]):
        cherrypick(commits=commits, cwd=self.root)

    def clean(self):
        command = ["git", "clean", "-fd"]
        run_subprocess(command=command, ex_type=GitError, cwd=self.root)

    @classmethod
    def from_yaml(cls, obj: Any):
        wt_obj = obj["worktree"]

        root = Path(wt_obj["root"])
        commit = wt_obj["commit"]
        branch = wt_obj["branch"]
        tag = wt_obj["tag"]
        locked = wt_obj["locked"]
        prunable = wt_obj["prunable"]

        worktree = cls(
            root=root,
            commit=commit,
            branch=branch,
            tag=tag,
            locked=locked,
            prunable=prunable,
        )

        return worktree

    def get_ref_and_type(self) -> Tuple[str, str]:
        if self.branch is not None:
            return self.branch, "branch"
        elif self.tag is not None:
            return self.tag, "tag"
        else:
            return self.commit, "commit"

    def has_untracked_files(self):
        """Check whether a git worktree has untracked files."""
        command = ["git", "ls-files", "--others", "--exclude-standard"]
        _, output = run_subprocess(command=command, ex_type=GitError, cwd=self.root)
        return output != ""

    def is_main(self) -> bool:
        return is_main_worktree(self.root)

    def switch(self, ref: str, ref_type: Optional[str] = None):
        old_ref, old_type = self.get_ref_and_type()

        if not ref_type:
            ref_type = disambiguate(ref)

        if ref_type not in ["commit", "branch", "tag"]:
            raise GitError(
                f"Failed to switch checkout of worktree {abbrev_home(self.root)}: "
                f"Object {ref!r} is not a known git reference."
            )

        git_checkout(ref=ref, cwd=self.root)

        # null the old ref type if necessary
        if ref_type != old_type:
            self.__setattr__(old_type, None)

        self.__setattr__(ref_type, ref)

        self.commit = resolve_commit(ref)

    def to_dict(self) -> Any:
        return {
            "root": abbrev_home(self.root),
            "ref": self.get_ref_and_type()[0],
        }

    def to_yaml(self) -> Any:
        obj = {
            "root": str(self.root),
            "commit": self.commit,
            "branch": self.branch,
            "tag": self.tag,
            "locked": self.locked,
            "prunable": self.prunable,
        }

        return {
            "worktree": obj,
        }


class TemporaryWorktree(TemporaryDirectory):
    """Temporary git worktree as context manager."""

    def __init__(
        self,
        commit_ish: str,
        force: bool = False,
        checkout: bool = True,
        extra_resources: Optional[List[str]] = None,
        cherrypicks: Optional[List[str]] = None,
    ):
        # tempdir is created in the constructor, saved under self.name
        super().__init__()
        self.commit_ish = commit_ish
        self.force = force
        self.checkout = checkout
        self.worktree = add(commit_ish=self.commit_ish, path=self.name, force=self.force)

        if extra_resources is not None:
            for resource in extra_resources:
                self.worktree.checkout(resource=resource)
        if cherrypicks is not None:
            self.worktree.cherrypick(commits=cherrypicks)

    def __enter__(self) -> Worktree:
        return self.worktree

    def __exit__(self, exc_type, exc_val, exc_tb):
        remove(self.worktree, force=True)
        super().__exit__(exc_type, exc_val, exc_tb)


@contextlib.contextmanager
def git_worktree_context(action: str, ref: str, ref_type: str, directory: Union[str, Path]):
    try:
        new_or_existing = "new" if action == "add" else "existing"
        where = "to new" if action == "move" else "in"

        if action.endswith("e"):
            action = action[:-1]
        print(
            f"{action.capitalize()}ing {new_or_existing} worktree for {ref_type} "
            f"{ref!r} {where} location {abbrev_home(directory)!r}.....",
            end="",
        )

        yield

        print("done.")
        print(
            f"Successfully {action}ed {new_or_existing} worktree for {ref_type} "
            f"{ref!r} {where} location {abbrev_home(directory)!r}."
        )
    except GitError:
        print("failed.")
        raise


def get_main_worktree() -> Worktree:
    # main worktree is always listed first
    return list_worktrees()[0]


def get_by_attr(attr: str, value: str, verbose: bool = False) -> Optional[Worktree]:
    # value: user-input, x: worktree object from `self.list()`
    attr_checks = {
        "root": lambda x: Path(value).name == Path(x).name,
        "commit": lambda x: x.startswith(value),  # commit SHA match at the start
        "branch": lambda x: value == x.split("/", maxsplit=2)[-1],
        "tag": lambda x: value == x.split("/", maxsplit=2)[-1],
    }

    assert attr in attr_checks, f"illegal worktree attribute {attr!r}"

    if verbose:
        print(f"Matching git worktree with {attr} {value!r}.....", end="")

    try:
        match = attr_checks[attr]
        worktree = next(worktree for worktree in list_worktrees() if match(getattr(worktree, attr)))

        if verbose:
            print("success.")
            ref, ref_type = worktree.get_ref_and_type()
            print(f"Matched worktree pointing to {ref_type} {ref!r}.")
        return worktree

    except StopIteration:
        if verbose:
            print("failed.")
        return None


def add(
    commit_ish: str,
    path: Optional[str] = None,
    force: bool = False,
    checkout: bool = True,
    lock: bool = False,
    verbose: bool = False,
):
    ref, ref_type = resolve_ref(commit_ish, resolve_commits=False)
    commit = resolve_commit(commit_ish)

    if verbose:
        print(f"Interpreting given reference {commit_ish!r} as a {ref_type} name.")

    # check for existing worktree with the same ref
    if not force and get_by_attr(ref_type, ref) is not None:
        msg = (
            f"Worktree for {ref_type} {commit_ish!r} already exists. If you want "
            f"to check out the same {ref_type} multiple times, supply the "
            f"-f/--force option to `pybm create`."
        )
        raise GitError(msg)

    if not path:
        # default worktree root name is <repo-name>@<ref>
        # TODO: Disallow Windows forbidden filechars as well if on Windows
        escaped = commit_ish.replace("/", "-")

        repo_name = main_worktree_directory().name
        worktree_dir = f"{repo_name}@{escaped}"

        # create relative to the desired directory
        path = str((Path.cwd().parent / worktree_dir))

    command = ["git", "worktree", "add", path, ref]

    if force:
        command += ["--force"]
    if lock:
        command += ["--lock"]
    if not checkout:
        command += ["--no-checkout"]

    with git_worktree_context("add", ref, ref_type, path):
        run_subprocess(command=command, ex_type=GitError)

    created_worktree = Worktree(
        root=Path(path),
        commit=commit,
        locked=lock,
    )
    setattr(created_worktree, ref_type, ref)

    return created_worktree


def list_worktrees() -> List[Worktree]:
    commit_tag_mapping = map_commits_to_tags()

    def _process(info: str) -> Worktree:
        lines = info.splitlines()
        splits = [line.split()[-1] for line in lines]

        if len(splits) < 3:
            raise PybmError("bare worktrees are not useable with pybm")

        root, commit, branch, *splits = splits
        if branch == "detached":
            branch = None  # type: ignore

        tag = commit_tag_mapping.get(commit, None)
        locked = any(line.startswith("locked") for line in lines)
        prunable = any(line.startswith("prunable") for line in lines)

        return Worktree(
            root=Path(root),
            commit=commit,
            branch=branch,
            tag=tag,
            locked=locked,
            prunable=prunable,
        )

    _, output = run_subprocess(["git", "worktree", "list", "--porcelain"])

    # porcelain outputs are separated with an empty line
    attr_list = output.strip().split("\n\n")

    return lmap(_process, attr_list)


def move(
    attr: Optional[str],
    info: str,
    new_path: Union[str, Path],
    verbose: bool = False,
):
    attr = attr or disambiguate(info)

    if not attr:
        # TODO: Display close matches if present
        msg = f"Argument {info!r} was not recognized as an attribute of an existing worktree."
        raise GitError(msg)

    worktree = get_by_attr(attr, info, verbose=verbose)

    if worktree is None:
        raise GitError(f"Worktree with {attr} {info!r} does not exist.")

    ref, ref_type = worktree.get_ref_and_type()
    root = worktree.root

    if Path(root) == Path(new_path):
        # no-op
        return

    with git_worktree_context("move", ref, ref_type, root):
        run_subprocess(command=["git", "worktree", "move", str(new_path)], ex_type=GitError)


def remove(worktree: Worktree, force=False, verbose: bool = False):
    ref, ref_type = worktree.get_ref_and_type()
    root = str(worktree.root)
    command = ["git", "worktree", "remove", root]

    if force:
        command += ["--force"]

    with git_worktree_context("remove", ref, ref_type, root):
        run_subprocess(command=command)

    return worktree


def repair(attr: Optional[str], info: str, verbose: bool = False):
    # avoid expensive call if attr is given
    attr = attr or disambiguate(info)

    if not attr:
        # TODO: Display close matches if present
        msg = f"Argument {info!r} was not recognized as an attribute of an existing worktree."
        raise GitError(msg)

    worktree = get_by_attr(attr, info, verbose=verbose)

    if worktree is None:
        raise GitError(f"Worktree with {attr} {info!r} does not exist.")

    ref, ref_type = worktree.get_ref_and_type()
    root = str(worktree.root)
    command = ["git", "worktree", "repair", root]

    with git_worktree_context("repair", ref, ref_type, root):
        run_subprocess(command=command)
