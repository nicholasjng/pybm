"""Small Git worktree wrapper for operating on a repository via Python."""
import contextlib
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Union

from pybm.config import PybmConfig
from pybm.exceptions import GitError
from pybm.logging import get_logger
from pybm.specs import Worktree
from pybm.util.common import lmap, lfilter, version_string
from pybm.util.git import (
    GIT_VERSION,
    disambiguate_info,
    resolve_ref,
    is_main_worktree,
    checkout as git_checkout,
    resolve_commit,
)
from pybm.util.path import current_folder
from pybm.util.print import abbrev_home
from pybm.util.subprocess import run_subprocess

# major, minor, micro
VersionTuple = Tuple[int, int, int]
GitCommandVersions = Dict[str, VersionTuple]
GitOptionVersions = Dict[str, Dict[str, VersionTuple]]

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
    """Wrapper class for a Git-based benchmark environment creator."""

    def __init__(self, config: PybmConfig):
        super().__init__()
        self.command_db = _git_worktree_flags
        self.base_dir: Path = Path(config.get_value("git.basedir"))

    def prepare_subprocess_args(self, command: str, *args, **kwargs):
        call_args = ["git", "worktree", command, *args]

        # parse git command line args separately
        call_args += self.parse_flags(command, **kwargs)

        return call_args

    def parse_flags(self, command: str, **kwargs):
        flags = []
        command_options = self.command_db[command]

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

    def run_command(self, worktree_command: str, *args, **kwargs) -> Tuple[int, str]:
        command = self.prepare_subprocess_args(worktree_command, *args, **kwargs)

        # check call args against git version
        self.feature_guard(command)

        logger.debug(f"Running command `{' '.join(command)}`.")

        return run_subprocess(command=command, ex_type=GitError)

    def get_worktree_by_attr(
        self, attr: str, value: str, verbose: bool = False
    ) -> Optional[Worktree]:
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

    def feature_guard(self, command: List[str]) -> None:
        worktree_command, *rest = command[2:]
        assert (
            worktree_command in self.command_db
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
            minimum = version_string(min_version)
            of_type = "switch" if offender.startswith("-") else "command"

            msg = (
                f"Running the command `{' '.join(command)}` requires at minimum git "
                f"version {minimum}, but your git version was found to be only "
                f"{version_string(GIT_VERSION)}. This version requirement exists "
                f"because the {of_type} {offender!r} was used, which was first "
                f"introduced in git version {minimum}."
            )

            raise GitError(msg)

    def list(self, porcelain: bool = True) -> List[Worktree]:
        _, output = self.run_command("list", porcelain=porcelain)

        # `git worktree list --porcelain` outputs are twice newline-terminated
        # at the end, creating an empty string when applying str.splitlines()
        attr_list = lfilter(lambda x: x != "", output.splitlines())

        # split off the attribute names and just collect the data
        attr_list = lmap(lambda x: x.split()[-1], attr_list)

        worktree_list = [attr_list[i : i + 3] for i in range(0, len(attr_list), 3)]

        return lmap(Worktree.from_list, worktree_list)

    def add(
        self,
        commit_ish: str,
        destination: Optional[str] = None,
        force: bool = False,
        checkout: bool = True,
        lock: bool = False,
        resolve_commits: bool = False,
        verbose: bool = False,
    ):
        current_directory = current_folder()

        if not is_main_worktree(current_directory):
            raise GitError("No git repository present in this path.")

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

            worktree_id = "@".join([current_directory.name, escaped])

            # create relative to the desired directory
            destination = str((self.base_dir / worktree_id).resolve())

        with git_worktree_context("add", ref, ref_type, destination):
            self.run_command(
                "add", destination, ref, force=force, checkout=checkout, lock=lock
            )

        # return worktree by attribute search
        return self.get_worktree_by_attr("root", destination)

    def move(self, worktree: Worktree, new_path: Union[str, Path]):
        ref, ref_type = worktree.get_ref_and_type()
        root = worktree.root

        with git_worktree_context("move", ref, ref_type, root):
            self.run_command("move", str(new_path))

    def remove(self, info: str, force=False, verbose: bool = False):
        if not is_main_worktree(current_folder()):
            raise GitError("No git repository present in this path.")

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
            self.run_command("remove", destination, force=force)

        return worktree

    def repair(self, worktree: Worktree):
        ref, ref_type = worktree.get_ref_and_type()
        root = worktree.root

        with git_worktree_context("repair", ref, ref_type, root):
            self.run_command("repair", root)

    def switch(self, worktree: Worktree, ref: str, ref_type: Optional[str] = None):
        old_ref, old_type = worktree.get_ref_and_type()

        if not ref_type:
            ref_type = disambiguate_info(ref)

        if ref_type not in ["commit", "branch", "tag"]:
            raise GitError(
                f"Failed to switch checkout of worktree {abbrev_home(worktree.root)}: "
                f"Object {ref!r} could not be understood as a valid git reference."
            )

        git_checkout(ref=ref, cwd=worktree.root)

        # null the old reference type if necessary
        if ref_type != old_type:
            setattr(worktree, old_type, None)

        setattr(worktree, ref_type, ref)

        worktree.commit = resolve_commit(ref)

        if old_ref in worktree.root:
            new_path = worktree.root.replace(old_ref, ref)
            # git worktree move renames the path on its own
            self.move(worktree=worktree, new_path=new_path)
            worktree.root = new_path

        print(
            f"Successfully checked out {ref_type} {ref!r} in worktree "
            f"{abbrev_home(worktree.root)}."
        )

        return worktree
