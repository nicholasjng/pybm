"""Small Git worktree wrapper for operating on a repository via Python."""
from pathlib import Path
from typing import Optional, List, Tuple, Dict

from pybm.config import PybmConfig
from pybm.exceptions import GitError
from pybm.logging import get_logger
from pybm.specs import Worktree
from pybm.util.subprocess import run_subprocess
from pybm.util.common import lmap, lfilter, version_string
from pybm.util.git import disambiguate_info, get_git_version, resolve_ref, \
    is_main_worktree
from pybm.util.path import current_folder

# major, minor, micro
VersionTuple = Tuple[int, int, int]
GitCommandVersions = Dict[str, VersionTuple]
GitOptionVersions = Dict[str, Dict[str, VersionTuple]]

# minimum git versions for worktree commands
_git_worktree_versions: GitCommandVersions = {
    "add": (2, 6, 7),
    "list": (2, 7, 6),
    "remove": (2, 17, 0),
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
    "remove": {
        "-f": (2, 17, 0),
    },
}

_git_worktree_flags = {
    "add": {"force": {True: "-f", False: None},
            "checkout": {True: None, False: "--no-checkout"},
            "lock": {True: "--lock", False: None},
            },
    "list": {"porcelain": {True: "--porcelain", False: None}},
    "remove": {"force": {True: "-f", False: None}}
}

logger = get_logger(__name__)


class GitWorktreeWrapper:
    """Wrapper class for a Git-based benchmark environment creator."""

    def __init__(self, config: PybmConfig):
        super().__init__()
        self.command_db = _git_worktree_flags
        self.create_in_parent = config.get_value(
            "git.createWorktreeInParentDirectory")

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
                logger.debug(f"Encountered unknown command line option {k} "
                             f"with value {v} for \"git worktree {command}\".")
                continue
            cmd_opts = command_options[k]
            flag = cmd_opts[v]
            if flag is not None:
                flags.append(flag)
        return flags

    def run_command(self, wt_command: str, *args, **kwargs) -> Tuple[int, str]:
        command = self.prepare_subprocess_args(wt_command, *args, **kwargs)
        # check call args against git version
        self.feature_guard(command)
        logger.debug(
            "Running command \"{cmd}\".".format(cmd=" ".join(command)))
        return run_subprocess(command=command, ex_type=GitError)

    def get_worktree_by_attr(self, attr: str, value: str) \
            -> Optional[Worktree]:
        attr_checks = {
            "root": lambda x: Path(x).name == Path(value).name,
            "commit": lambda x: value in x,  # partial commit match
            "branch": lambda x: x.split("/")[-1] == value,
            "tag": lambda x: x.split("/")[-1] == value,
        }
        assert attr in attr_checks, f"illegal worktree attribute {attr!r}"
        # TODO: What to do here if someone force-checks out the same ref twice?
        try:
            match = attr_checks[attr]
            return next(
                wt for wt in self.list_worktrees() if match(getattr(wt, attr))
            )
        except StopIteration:
            return None

    def feature_guard(self, command: List[str]) -> None:
        wt_command, *rest = command[2:]
        assert wt_command in self.command_db, \
            f"unimplemented git worktree command \"{wt_command}\""

        min_version = _git_worktree_versions[wt_command]
        options = _git_option_versions[wt_command]
        installed = get_git_version()
        # log offender and type (command/switch) for dynamic errors
        offender, of_type = wt_command, "command"

        for k in lfilter(lambda x: x.startswith("-"), rest):
            if k in options:
                contender: VersionTuple = options[k]
                if contender > min_version:
                    min_version = contender
                    offender, of_type = k, "switch"
        if installed < min_version:
            full_command = " ".join(command)
            minimum = version_string(min_version)
            actual = version_string(installed)
            msg = f"Running the command {full_command!r} requires a " \
                  f"minimum git version of {minimum}, but your git " \
                  f"version was found to be only {actual}. " \
                  f"This version requirement is because the {of_type} " \
                  f"{offender!r} was used, which was first introduced in " \
                  f"git version {minimum}."
            raise GitError(msg)

    def list_worktrees(self, porcelain: bool = True) -> List[Worktree]:
        _, output = self.run_command("list", porcelain=porcelain)
        # git worktree list porcelain outputs are twice newline-terminated
        # at the end, creating an empty string when applying str.splitlines()
        attr_list = lfilter(lambda x: x != "", output.splitlines())
        # split off the attribute names and just collect the data
        attr_list = lmap(lambda x: x.split()[-1], attr_list)
        wt_list = [attr_list[i:i + 3] for i in range(0, len(attr_list), 3)]
        return lmap(Worktree.from_list, wt_list)

    def add_worktree(self, commit_ish: str,
                     destination: Optional[str] = None,
                     force: bool = False,
                     checkout: bool = True,
                     lock: bool = False,
                     resolve_commits: bool = False,
                     verbose: bool = False):
        current_directory = current_folder()

        if not is_main_worktree(current_directory):
            raise GitError("No git repository present in this path.")

        ref, ref_type = resolve_ref(commit_ish,
                                    resolve_commits=resolve_commits)
        if verbose:
            print(f"Interpreting given git ref {commit_ish!r} "
                  f"as a {ref_type} name.")

        # check for existing worktree with the same ref
        if not force and self.get_worktree_by_attr(ref_type, ref):
            msg = f"Worktree for {ref_type} {commit_ish!r} already exists. " \
                  f"If you want to check out the same {ref_type} " \
                  f"multiple times, supply the -f/--force option to " \
                  f"`pybm create`."
            raise GitError(msg)

        if not destination:
            # default worktree root name is repo@<ref>
            # TODO: Refactor this into a convenience function
            escaped = commit_ish.replace("/", "-")
            worktree_id = "@".join([current_directory.name, escaped])
            # create relative to the desired directory
            if self.create_in_parent:
                dest_dir = current_directory.parent
            else:
                dest_dir = current_directory
            destination = str(dest_dir / worktree_id)

        print(f"Adding worktree for ref {ref!r} in directory {destination}"
              f".....", end="")
        self.run_command("add", destination, ref, force=force,
                         checkout=checkout, lock=lock)
        print("done.")

        # return worktree by attribute search
        wt = self.get_worktree_by_attr("root", destination)
        assert wt is not None, "internal error in git worktree construction"
        return wt

    def remove_worktree(self, info: str, force=False, verbose: bool = False):
        if not is_main_worktree(current_folder()):
            raise GitError("No git repository present in this path.")

        attr = disambiguate_info(info)
        if not attr:
            # TODO: Display close matches if present
            msg = f"Argument {info!r} was not recognized as an attribute of " \
                  f"an existing environment worktree."
            raise GitError(msg)
        if verbose:
            print(f"Given identifier {info} was determined to be "
                  f"the {attr!r} attribute of the desired worktree.")

        print(f"Matching git worktree with {attr} {info!r}.....", end="")
        wt = self.get_worktree_by_attr(attr, info)
        if wt is None:
            print("failed.")
            msg = f"Worktree with associated {attr} {info!r} " \
                  f"does not exist."
            raise GitError(msg)
        print("success.")

        ref, ref_type = wt.get_ref_and_type()
        print(f"Matched worktree pointing to {ref_type} {ref!r}.")
        print(f"Removing worktree at location {wt.root}.....", end="")
        self.run_command("remove", wt.root, force=force)
        print("done.")
        return wt
