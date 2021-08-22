"""Small Git worktree wrapper for operating on a repository via Python."""

import subprocess
from pathlib import Path
from typing import Optional, List, Dict
from pybm.exceptions import GitError
from pybm.git_utils import lmap, get_repository_name, \
    list_local_branches, resolve_commit, lfilter, resolve_to_ref, \
    git_worktree_feature_guard

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


class GitWorktreeWrapper(CommandWrapperMixin):
    """Wrapper class for a Git-based benchmark environment creator."""

    def __init__(self):
        super().__init__(command_db=_git_worktree_flags,
                         exception_type=GitError)
        self.executable = "git"
        self.worktrees = self.list_worktrees()
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
        return self.wrapped_subprocess_call(name="run",
                                            call_args=call_args,
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.PIPE,
                                            check=True,
                                            encoding="utf-8")

    def get_worktree_by_name(self, name: str):
        worktrees = self.list_worktrees()
        try:
            # absolute paths, match names against bottom level directories
            wt = next(wt for wt in worktrees if wt["worktree"].endswith(name))
        except StopIteration:
            wt = None
        return wt

    def get_worktree_by_commit(self, commit_sha: str):
        worktrees = self.list_worktrees()
        try:
            # partial matching commit SHA with `in`, returns first occurrence
            wt = next(wt for wt in worktrees if commit_sha in wt["HEAD"])
        except StopIteration:
            wt = None
        return wt

    def get_worktree_by_branch(self, name: str):
        worktrees = self.list_worktrees()
        try:
            # branches are in the form refs/heads/$BRANCH or "detached"
            wt = next(wt for wt in worktrees if wt["branch"].split("/")[-1]
                      == name)
        except StopIteration:
            wt = None
        return wt

    def get_worktree_by_ref_type(self, ref: str, ref_type: str):
        handlers = {
            "tag": lambda x: self.get_worktree_by_commit(resolve_commit(x)),
            "branch": self.get_worktree_by_branch,
            "commit": self.get_worktree_by_commit
        }
        return handlers.get(ref_type)(ref)

    def list_worktrees(self, porcelain: bool = True) -> List[Dict[str, str]]:
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

    def add_worktree(self, commit_ish: str, name: Optional[str] = None,
                     force: bool = False, checkout: bool = True,
                     lock: bool = False, resolve_commits: bool = False):

        ref, ref_type = resolve_to_ref(commit_ish,
                                       resolve_commits=resolve_commits)

        # check for existing worktree with the same spec
        if not force and self.get_worktree_by_ref_type(ref, ref_type=ref_type):
            msg = f"Worktree for {ref_type} {commit_ish} already exists. " \
                  f"If you want to check out the same {ref_type} " \
                  f"multiple times, supply the -f/--force option to " \
                  f"`pybm create`."
            raise GitError(msg)

        if not name:
            # TODO: Fallback if the designated directory exists
            # worktree name repo@<ref> in the current directory
            escaped = commit_ish.replace("/", "-")
            name = "@".join([self.repository_name, escaped])

        return self.run_command("add", name, ref, force=force,
                                checkout=checkout, lock=lock)

    def remove_worktree(self, info: str, force=False):
        # TODO: Improve info disambiguation - path match against repository
        #  name, branch match local vs. remote, commit partial match
        p = Path("./")
        # All subdirectories in the current directory, not recursive.
        all_subdirs = [f.stem for f in filter(Path.is_dir, p.iterdir())]
        if info in all_subdirs:
            wt, wt_id = self.get_worktree_by_name(info), "directory name"
        elif info in list_local_branches():
            wt, wt_id = self.get_worktree_by_branch(info), "branch name"
        else:
            wt, wt_id = self.get_worktree_by_commit(info), "commit"

        if not wt:
            msg = f"Worktree with {wt_id} {info} does not exist."
            raise GitError(msg)

        return self.run_command("remove", info, force=force)


git = GitWorktreeWrapper()
