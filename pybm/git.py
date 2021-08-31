"""Small Git worktree wrapper for operating on a repository via Python."""
import os
from typing import Optional, List, Dict, Text, Union, Tuple
from pybm.exceptions import GitError, ArgumentError
from pybm.git_utils import lmap, resolve_commit, \
    lfilter, resolve_to_ref, disambiguate_info, get_git_version
from pybm.path_utils import current_folder_name, get_subdirs
from pybm.subprocessing import CommandWrapperMixin

# major, minor, micro
VersionTuple = Tuple[int, int, int]
OptionDict = Dict[Text, VersionTuple]
GitCommandVersions = Dict[Text, VersionTuple]
GitOptionVersions = Dict[Text, OptionDict]
Worktree = Dict[Text, Text]

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
            "checkout": {True: "--checkout", False: "--no-checkout"},
            "lock": {True: "--lock", False: None},
            },
    "list": {"porcelain": {True: "--porcelain", False: None}},
    "remove": {"force": {True: "-f", False: None}}
}


class GitWorktreeWrapper(CommandWrapperMixin):
    """Wrapper class for a Git-based benchmark environment creator."""

    def __init__(self):
        super().__init__(exception_type=GitError)
        self.command_db = _git_worktree_flags

    @staticmethod
    def is_git_repository(path: str):
        subdirs = get_subdirs(path)
        return ".git" in subdirs

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
                # TODO: log bad kwarg usage somewhere
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

        return self.run_subprocess(command=command)

    def get_worktree_by_attr(self, attr: str, value: str) -> \
            Union[Worktree, None]:
        attr_checkers = {
            "worktree": lambda x: os.path.abspath(value) == x,
            "HEAD": lambda x: value in x,
            "branch": lambda x: x.split("/")[-1] == value,
            "tag": lambda x: value in resolve_commit(x),
            "commit": lambda x: value in x,
        }
        assert attr in attr_checkers, f"got illegal worktree attribute {attr}"
        try:
            match = attr_checkers[attr]
            return next(wt for wt in self.list_worktrees() if match(wt[attr]))
        except StopIteration:
            return None

    @staticmethod
    def make_worktree_spec(attribute_list: List[str]) -> Worktree:
        # TODO: Choose better attribute names for environments than the git
        #  defaults
        wt_info: List[List[str]] = lmap(str.split, attribute_list)
        wt: Worktree = {k: v for k, v in wt_info}
        return wt

    @staticmethod
    def feature_guard(command: List[str]):
        def version_string(x):
            return ".".join(map(str, x))

        assert len(command) > 2 and command[:2] == ["git", "worktree"], \
            "internal git command construction error"

        worktree_command, rest = command[2], command[2:]
        assert worktree_command in _git_option_versions, \
            f"unimplemented git worktree command `{worktree_command}`"

        min_version = _git_worktree_versions[worktree_command]
        options = _git_option_versions[worktree_command]
        # log offending command or option for dynamic exception printing
        newest = worktree_command

        for k in lfilter(lambda x: x.startswith("-"), rest):
            if k in options:
                contender: VersionTuple = options[k]
                if contender > min_version:
                    min_version = contender
                    newest = k

        installed = get_git_version()
        if installed < min_version:
            full_command = " ".join(command)
            min_string = version_string(min_version)
            installed_string = version_string(installed)
            identifier = "option" if newest.startswith("-") else "command"
            msg = f"Running the command `{full_command}` requires a " \
                  f"minimum git version of {min_string}, but your git " \
                  f"version was found to be only {installed_string}. " \
                  f"This version requirement is because the {identifier} " \
                  f"`{newest}` was used, which was first introduced in " \
                  f"git version {min_string}."
            raise GitError(msg)

    def list_worktrees(self, porcelain: bool = True) -> List[Worktree]:
        _, output = self.run_command("list", porcelain=porcelain)
        # git worktree porcelain lists are twice newline-terminated at the end,
        # creating an empty string when applying str.splitlines()
        attr_list = lfilter(lambda x: x != "", output.splitlines())
        # detached HEADs have no associated branch, prepend the attribute so
        # that we produce the same dictionary schema every time
        attr_list = lmap(
            lambda x: "branch " + x if x == "detached" else x,
            attr_list)
        # worktree attributes are directory, HEAD and branch
        wt_list = [attr_list[i:i + 3] for i in range(0, len(attr_list), 3)]
        return lmap(self.make_worktree_spec, wt_list)

    def add_worktree(self, commit_ish: str,
                     destination: Optional[str] = None,
                     force: bool = False,
                     checkout: bool = True,
                     lock: bool = False,
                     resolve_commits: bool = False) -> Worktree:
        current_directory = current_folder_name()

        if not self.is_git_repository(current_directory):
            raise ArgumentError("No git repository present in this path.")

        ref, ref_type = resolve_to_ref(commit_ish,
                                       resolve_commits=resolve_commits)

        # check for existing worktree with the same spec
        if not force and self.get_worktree_by_attr(ref_type, ref):
            msg = f"Worktree for {ref_type} {commit_ish} already exists. " \
                  f"If you want to check out the same {ref_type} " \
                  f"multiple times, supply the -f/--force option to " \
                  f"`pybm create`."
            raise ArgumentError(msg)

        if not destination:
            # worktree name repo@<ref> in the current directory
            escaped = commit_ish.replace("/", "-")
            worktree_id = "@".join([current_directory, escaped])
            destination = os.path.abspath(worktree_id)

        self.run_command("add", destination, ref, force=force,
                         checkout=checkout, lock=lock)

        # return worktree by attribute search
        wt = self.get_worktree_by_attr("worktree", destination)
        assert wt is not None, "internal error in git worktree construction"
        return wt

    def remove_worktree(self, info: str, force=False) -> Worktree:
        if not self.is_git_repository(current_folder_name()):
            raise ArgumentError("No git repository present in this path.")

        attr = disambiguate_info(info)

        wt = self.get_worktree_by_attr(attr, info)
        if wt is None:
            msg = f"Worktree with associated attribute {attr} does not exist."
            raise ArgumentError(msg)

        self.run_command("remove", wt["worktree"], force=force)

        return wt


git = GitWorktreeWrapper()
