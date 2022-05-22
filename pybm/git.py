"""Small Git worktree wrapper for operating on a repository via Python."""
import contextlib
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple, Union

from pybm.config import config
from pybm.exceptions import GitError
from pybm.logging import get_logger
from pybm.util.common import lfilter, lmap, version_string
from pybm.util.formatting import abbrev_home
from pybm.util.git import (
    GIT_VERSION,
    disambiguate_info,
    is_main_worktree,
    map_commits_to_tags,
    resolve_ref,
)
from pybm.util.path import current_folder
from pybm.util.subprocess import run_subprocess

# major, minor, micro
VersionTuple = Tuple[int, int, int]
GitCommandVersions = Dict[str, VersionTuple]
GitOptionVersions = Dict[str, Dict[str, VersionTuple]]


class GitWorktree(NamedTuple):
    root: str
    commit: str
    branch: Optional[str]
    tag: Optional[str]
    locked: bool = False
    prunable: bool = False

    def get_ref_and_type(self) -> Tuple[str, str]:
        if self.branch is not None:
            return self.branch, "branch"
        elif self.tag is not None:
            return self.tag, "tag"
        else:
            return self.commit, "commit"

    def is_main(self) -> bool:
        return is_main_worktree(self.root)


# minimum git versions for worktree commands
_git_worktree_versions: GitCommandVersions = {
    "add": (2, 6, 7),
    "list": (2, 7, 6),
    "move": (2, 17, 0),
    "remove": (2, 17, 0),
    "repair": (2, 30, 0),
}

# minimum git versions for worktree command options
_git_option_versions: GitOptionVersions = {
    "add": {
        "-f": (2, 6, 7),
        "--checkout": (2, 9, 5),
        "--no-checkout": (2, 9, 5),
        "--lock": (2, 13, 7),
    },
    "list": {
        "--porcelain": (2, 7, 6),
    },
    "move": {},
    "remove": {
        "-f": (2, 17, 0),
    },
    "repair": {},
}

_git_worktree_flags = {
    "add": {
        "force": {True: "-f", False: None},
        "checkout": {True: None, False: "--no-checkout"},
        "lock": {True: "--lock", False: None},
    },
    "list": {"porcelain": {True: "--porcelain", False: None}},
    "remove": {"force": {True: "-f", False: None}},
}

logger = get_logger(__name__)


@contextlib.contextmanager
def git_worktree_context(
    action: str, ref: str, ref_type: str, directory: Union[str, Path]
):
    try:
        new_or_existing = "new" if action == "create" else "existing"
        where = "to new" if action == "move" else "in"

        if action.endswith("e"):
            action = action[:-1]
        print(
            f"{action.capitalize()}ing {new_or_existing} worktree for {ref_type} "
            f"{ref!r} {where} location {abbrev_home(directory)}.....",
            end="",
        )

        yield

        print("done.")
        print(
            f"Successfully {action}ed {new_or_existing} worktree for {ref_type} "
            f"{ref!r} {where} location {abbrev_home(directory)}."
        )
    except GitError:
        print("failed.")
        raise


class GitWorktreeWrapper:
    """Wrapper class for the `git worktree` class of subcommands."""

    def __init__(self):
        # self.command_db = _git_worktree_flags
        self.base_dir: Path = Path(config.get_value("git.basedir"))

    def _prepare_subprocess_args(self, command: str, *args, **kwargs):
        call_args = ["git", "worktree", command, *args]

        # parse git command line args separately
        call_args += self._parse_flags(command, **kwargs)

        return call_args

    @staticmethod
    def _parse_flags(command: str, **kwargs):
        flags = []
        command_options = _git_worktree_flags[command]

        for k, v in kwargs.items():
            if k not in command_options:
                logger.debug(
                    f"Encountered unknown command line option {k!r} with value {v!r} "
                    f"for `git worktree {command}`."
                )
                continue

            cmd_opts = command_options[k]
            flag = cmd_opts[v]

            if flag is not None:
                flags.append(flag)

        return flags

    def _run_command(self, worktree_command: str, *args, **kwargs) -> Tuple[int, str]:
        command = self._prepare_subprocess_args(worktree_command, *args, **kwargs)

        # check call args against git version
        self._feature_guard(command)

        logger.debug(f"Running command `{' '.join(command)}`.")

        return run_subprocess(command=command, ex_type=GitError)

    def get_main_worktree(self) -> GitWorktree:
        # main worktree is always listed first
        return self.list()[0]

    def get_worktree_by_attr(
        self, attr: str, value: str, verbose: bool = False
    ) -> Optional[GitWorktree]:
        # value: user-input, x: worktree object from `self.list()`
        attr_checks = {
            "root": lambda x: Path(value).name == Path(x).name,
            "commit": lambda x: value in x,  # partial commit match
            "branch": lambda x: value == x.split("/", maxsplit=2)[-1],
            "tag": lambda x: value == x.split("/", maxsplit=2)[-1],
        }

        assert attr in attr_checks, f"illegal worktree attribute {attr!r}"

        # TODO: What to do here if someone force-checks out the same ref twice?
        if verbose:
            print(f"Matching git worktree with {attr} {value!r}.....", end="")

        try:
            match = attr_checks[attr]
            worktree = next(
                worktree for worktree in self.list() if match(getattr(worktree, attr))
            )

            if verbose:
                print("success.")
                ref, ref_type = worktree.get_ref_and_type()
                print(f"Matched worktree pointing to {ref_type} {ref!r}.")
            return worktree

        except StopIteration:
            if verbose:
                print("failed.")
            return None

    @staticmethod
    def _feature_guard(command: List[str]) -> None:
        worktree_command, *rest = command[2:]
        assert (
            worktree_command in _git_worktree_flags
        ), f"unimplemented git worktree command {worktree_command!r}."

        min_version = _git_worktree_versions[worktree_command]
        options = _git_option_versions[worktree_command]
        # log offender and type (command/switch) for dynamic errors
        offender: str = worktree_command

        for k in lfilter(lambda x: x.startswith("-"), rest):
            if k in options:
                contender: VersionTuple = options[k]
                if contender > min_version:
                    min_version = contender
                    offender = k

        if GIT_VERSION < min_version:
            minimum, actual = version_string(min_version), version_string(GIT_VERSION)
            of_type = "switch" if offender.startswith("-") else "command"

            msg = (
                f"Running the command `{' '.join(command)}` requires at minimum git "
                f"version {minimum}, but your git version was found to be only "
                f"{actual}. This version requirement exists because the {of_type} "
                f"{offender!r} was used, first introduced in git version {minimum}."
            )

            raise GitError(msg)

    def add(
        self,
        commit_ish: str,
        destination: Optional[str] = None,
        create_branch: Optional[str] = None,
        force: bool = False,
        checkout: bool = True,
        lock: bool = False,
        resolve_commits: bool = False,
        verbose: bool = False,
    ):
        ref, ref_type = resolve_ref(commit_ish, resolve_commits=resolve_commits)

        if verbose:
            print(f"Interpreting given reference {commit_ish!r} as a {ref_type} name.")

        # check for existing worktree with the same ref
        if not force and self.get_worktree_by_attr(ref_type, ref) is not None:
            msg = (
                f"Worktree for {ref_type} {commit_ish!r} already exists. If you want "
                f"to check out the same {ref_type} multiple times, supply the "
                f"-f/--force option to `pybm create`."
            )
            raise GitError(msg)

        if not destination:
            # default worktree root name is repo@<ref>
            # TODO: Disallow Windows forbidden filechars as well if on Windows
            escaped = commit_ish.replace("/", "-")

            worktree_id = "@".join([current_folder().name, escaped])

            # create relative to the desired directory
            destination = str((self.base_dir / worktree_id).resolve())

        args = [destination, ref]

        if create_branch is not None:
            # create branch with HEAD commit_ish and check it out in the new worktree
            args += [f"-b {create_branch}"]

        with git_worktree_context("add", ref, ref_type, destination):
            self._run_command("add", *args, force=force, checkout=checkout, lock=lock)

        # return worktree by attribute search
        return self.get_worktree_by_attr("root", destination)

    def list(self, porcelain: bool = True) -> List[GitWorktree]:
        commit_tag_mapping = map_commits_to_tags()

        def _process(info: str) -> GitWorktree:
            worktree_obj: Dict[str, Union[str, bool, None]] = {}

            for line in info.splitlines():
                try:
                    attr, value = line.split(maxsplit=1)
                except ValueError:
                    # no value, e.g. with detached HEAD, or locked without reason
                    attr, value = line, ""

                # TODO: Handle bare worktrees (disallow?)
                if attr == "worktree":
                    worktree_obj["root"] = value
                elif attr == "HEAD":
                    # value is commit SHA
                    worktree_obj["commit"] = value
                    worktree_obj["tag"] = commit_tag_mapping.get(value, None)
                elif attr == "branch":
                    # all branches are implicitly locally tracked
                    worktree_obj["branch"] = value.split("/")[-1]
                elif attr == "detached":
                    worktree_obj["branch"] = None
                elif attr == "locked":
                    worktree_obj["locked"] = True
                elif attr == "prunable":
                    worktree_obj["prunable"] = True

            # locked and prunable are false by default in class spec
            return GitWorktree(**worktree_obj)  # type: ignore

        _, output = self._run_command("list", porcelain=porcelain)

        # porcelain outputs are separated with an empty line
        attr_list = output.strip().split("\n\n")

        return lmap(_process, attr_list)

    def move(
        self,
        attr: Optional[str],
        info: str,
        new_path: Union[str, Path],
        verbose: bool = False,
    ):
        attr = attr or disambiguate_info(info)

        if not attr:
            # TODO: Display close matches if present
            msg = (
                f"Argument {info!r} was not recognized as an attribute of an existing "
                f"worktree."
            )
            raise GitError(msg)

        worktree = self.get_worktree_by_attr(attr, info, verbose=verbose)

        if worktree is None:
            raise GitError(f"Worktree with {attr} {info!r} does not exist.")

        ref, ref_type = worktree.get_ref_and_type()
        root = worktree.root

        if Path(root) == Path(new_path):
            # no-op
            return

        with git_worktree_context("move", ref, ref_type, root):
            self._run_command("move", str(new_path))

    def remove(self, info: str, force=False, verbose: bool = False):
        attr = disambiguate_info(info)

        if not attr:
            # TODO: Display close matches if present
            msg = (
                f"Argument {info!r} was not recognized as an attribute of an existing "
                f"worktree."
            )
            raise GitError(msg)

        if verbose:
            print(
                f"Given identifier {info!r} was determined to be the {attr!r} "
                f"attribute of the desired worktree."
            )

        worktree = self.get_worktree_by_attr(attr, info, verbose=verbose)

        if worktree is None:
            raise GitError(f"Worktree with {attr} {info!r} does not exist.")

        ref, ref_type = worktree.get_ref_and_type()
        destination = worktree.root

        with git_worktree_context("remove", ref, ref_type, destination):
            self._run_command("remove", destination, force=force)

        return worktree

    def repair(self, attr: Optional[str], info: str, verbose: bool = False):
        # avoid expensive call if attr is given
        attr = attr or disambiguate_info(info)

        if not attr:
            # TODO: Display close matches if present
            msg = (
                f"Argument {info!r} was not recognized as an attribute of an existing "
                f"worktree."
            )
            raise GitError(msg)

        worktree = self.get_worktree_by_attr(attr, info, verbose=verbose)

        if worktree is None:
            raise GitError(f"Worktree with {attr} {info!r} does not exist.")

        ref, ref_type = worktree.get_ref_and_type()
        root = worktree.root

        with git_worktree_context("repair", ref, ref_type, root):
            self._run_command("repair", root)
