"""Small Git worktree wrapper for operating on a repository via Python."""

import subprocess
from typing import Optional, List, Dict, Union
from pybm.exceptions import GitError
from pybm.git_utils import parse_flags, lmap, get_repository_name, list_tags, \
    list_local_branches, resolve_commit, lfilter

WORKTREE_ATTRS = ["worktree", "branch", "HEAD"]


class GitWorktreeWrapper:
    """Wrapper class for a Git-based benchmark environment creator."""

    def __init__(self):
        self.executable = "git"
        self.repository_name = get_repository_name()

    def run_command(self, command: str, *args, **kwargs) -> str:
        call_args = [self.executable, "worktree", command]

        call_args.extend(list(args))
        # parse git command line args separately
        call_args.extend(parse_flags(command, **kwargs))
        try:
            return subprocess.check_output(call_args).decode("utf-8")
        except subprocess.CalledProcessError as e:
            full_command = " ".join(call_args)
            msg = f"The command `git {full_command}` returned the non-zero " \
                  f"exit code {e.returncode}. Further information (output of " \
                  f"the subprocess):\n {e.output}"
            raise GitError(msg)

    def get_worktree_by_attr(self, attr: Union[str, List[str]], value: str):
        worktrees = self.list_worktrees()
        attrs, wt = attr if isinstance(attr, str) else attr, None
        for attr in attrs:
            try:
                # all values are strings, so partial matching can be employed
                # with the `in` operator here
                wt = next(wt for wt in worktrees if wt[attr] in value)
            except StopIteration:
                continue
        return wt

    def list_worktrees(self) -> List[Dict[str, str]]:
        attr_list = self.run_command("list", "--porcelain").splitlines()
        # git worktree porcelain lists are twice newline-terminated at the end,
        # creating an empty string when applying str.splitlines() - these are
        # filtered out here
        attr_list = lfilter(lambda x: x != "", attr_list)
        num_attrs = len(attr_list)
        # detached HEADs have no associated branch, prepend the attribute so
        # that we produce the same dictionary schema every time
        attr_list = lmap(
            lambda x: str.split("branch " + x if x == "detached" else x),
            attr_list)
        # worktree attributes are directory, HEAD and branch
        attr_list = [attr_list[i:i+3] for i in range(0, num_attrs, 3)]
        return lmap(dict, attr_list)

    def add_worktree(self, commit_ish: str, name: Optional[str] = None,
                     force: bool = False, checkout: bool = False,
                     lock: bool = False, resolve_commits: bool = False):

        if not force and self.get_worktree_by_attr(WORKTREE_ATTRS, commit_ish):
            msg = f"fatal: Worktree with ID {commit_ish} already exists. If " \
                  f"you want to check out the same ref multiple times, " \
                  f"supply the -f/--force option to `pybm create`."
            raise GitError(msg)

        ref = commit_ish
        if resolve_commits:
            # TODO: Resolving is ambiguous if there are branches and tags
            #  with the same name. Figure this out
            if commit_ish in list_tags():
                # ref is a tag name
                ref = resolve_commit(commit_ish, ref_type="tag")
            elif commit_ish in list_local_branches():
                # ref is a branch name, check it out at HEAD
                ref = resolve_commit(commit_ish, ref_type="branch")
            else:
                pass

        if not name:
            # TODO: Fallback if the designated directory exists
            # worktree name repo@<sha> in the current directory
            name = "@".join([self.repository_name, ref])

        return self.run_command("add", name, ref, force=force,
                                checkout=checkout, lock=lock)

    def remove_worktree(self, info: str, force=False):
        # find worktree by commit or tag
        rm_worktree = self.get_worktree_by_attr(WORKTREE_ATTRS, info)
        if not rm_worktree:
            msg = f"fatal: Worktree with ID {info} does not exist."
            raise GitError(msg)

        return self.run_command("remove", info, force=force)
