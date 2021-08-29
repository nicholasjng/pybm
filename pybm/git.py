"""Small Git worktree wrapper for operating on a repository via Python."""
import os
import subprocess
from typing import Optional, List, Dict, Text, Union
from pybm.exceptions import GitError, ArgumentError
from pybm.git_utils import lmap, get_repository_name, resolve_commit, \
    lfilter, resolve_to_ref, git_worktree_feature_guard, disambiguate_info

# small git flag database for worktree commands
from pybm.subprocessing import CommandWrapperMixin

_git_worktree_flags = {
    "add": {"force": {True: "-f", False: None},
            "checkout": {True: "--checkout", False: "--no-checkout"},
            "lock": {True: "--lock", False: None},
            },
    "list": {"porcelain": {True: "--porcelain", False: None}},
    "remove": {"force": {True: "-f", False: None}}
}

Worktree = Dict[Text, Text]


class GitWorktreeWrapper(CommandWrapperMixin):
    """Wrapper class for a Git-based benchmark environment creator."""

    def __init__(self):
        super().__init__(command_db=_git_worktree_flags,
                         exception_type=GitError)
        self.executable = "git"
        self.repository_name = get_repository_name()

    def prepare_subprocess_args(self, command: str, *args, **kwargs):
        call_args = [self.executable, "worktree", command, *args]
        # parse git command line args separately
        call_args += self.parse_flags(command, **kwargs)
        return call_args

    def return_output(self, command: str, *args, **kwargs):
        call_args = self.prepare_subprocess_args(command, *args, **kwargs)
        git_worktree_feature_guard(call_args)
        return self.wrapped_subprocess_call("check_output",
                                            call_args=call_args,
                                            encoding="utf-8")

    def run_command(self, command: str, *args, **kwargs) -> int:
        call_args = self.prepare_subprocess_args(command, *args, **kwargs)
        git_worktree_feature_guard(call_args)
        return self.wrapped_subprocess_call("run",
                                            call_args=call_args,
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.PIPE,
                                            check=True,
                                            encoding="utf-8")

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
            wt: Worktree = next(wt for wt in self.list_worktrees() if
                                match(wt[attr]))
            return wt
        except StopIteration:
            return None

    def list_worktrees(self, porcelain: bool = True) -> List[Worktree]:
        attr_list = self.return_output("list",
                                       porcelain=porcelain).splitlines()
        # git worktree porcelain lists are twice newline-terminated at the end,
        # creating an empty string when applying str.splitlines()
        attr_list = lfilter(lambda x: x != "", attr_list)
        # detached HEADs have no associated branch, prepend the attribute so
        # that we produce the same dictionary schema every time
        attr_list = lmap(
            lambda x: str.split("branch " + x if x == "detached" else x),
            attr_list)
        # worktree attributes are directory, HEAD and branch
        attr_list = [attr_list[i:i + 3] for i in range(0, len(attr_list), 3)]
        return lmap(dict, attr_list)

    def add_worktree(self, commit_ish: str,
                     destination: Optional[str] = None,
                     force: bool = False, checkout: bool = True,
                     lock: bool = False, resolve_commits: bool = False):

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
            worktree_id = "@".join([self.repository_name, escaped])
            destination = os.path.abspath(worktree_id)

        self.run_command("add", destination, ref, force=force,
                         checkout=checkout, lock=lock)

        # return worktree by attribute search
        return self.get_worktree_by_attr("worktree", destination)

    def remove_worktree(self, info: str, force=False):
        attr = disambiguate_info(info)

        wt = self.get_worktree_by_attr(attr, info)
        if wt is None:
            msg = f"Worktree with associated attribute {attr} does not exist."
            raise ArgumentError(msg)

        return self.run_command("remove", wt["worktree"], force=force)


git = GitWorktreeWrapper()
