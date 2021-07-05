"""Small Git wrapper for operating on a repository via Python."""

import subprocess
import re
import os
from typing import Optional, Tuple, List, Dict

class GitWrapper:
    """Wrapper class for a Git-based benchmark environment creator."""
    def __init__(self):
        self.worktrees = self.list_worktrees()
        self.executable = "git"
        self.repository_name = ""

    def run_command(self, command: str, subcommand: Optional[str] = None,
                    *args, **kwargs) -> str:
        call_args = [self.executable, command]
        if subcommand is not None:
            call_args.append(subcommand)

        call_args += list(args)

        # TODO: Handle kwargs as additional command line args to git
        return subprocess.check_output(call_args).decode("utf-8")

    def get_version(self) -> Tuple[int]:
        output = self.run_command("--version")
        version_string = re.search(r'([\d.]+)', output).group()
        version_ints = map(int, version_string.split("."))
        return tuple(version_ints)

    @staticmethod
    def is_git_repository():
        # Check relative to current path, assumes everything is working.
        return os.path.exists(".git")

    def list_worktrees(self) -> List[Dict[str, str]]:
        worktree_string = self.run_command("worktree", "list")
        worktree_lists = map(str.split, worktree_string.splitlines())
        # order of listed git worktree data
        keys = ["root", "commit", "branch"]
        worktree_dicts = map(lambda x: dict(zip(keys, x)), worktree_lists)
        return list(worktree_dicts)

    def list_tags(self):
        return self.run_command("tag").splitlines()

    def add_worktree(self, commit_or_tag: str, name: Optional[str] = None,
                     **kwargs):
        if any(commit_or_tag in wt for wt in self.worktrees):
            msg = f"fatal: Worktree with ID {commit_or_tag} already exists."
            return msg

        if commit_or_tag in self.list_tags(): # ID is a tag
            # use tags/$TAG syntax to avoid ambiguity
            ref_commit = self.run_command("rev-list", None, "-n", "1",
                                          f"tags/{commit_or_tag}")
        else: # it is a commit SHA
            ref_commit = commit_or_tag

        if not name:
            # worktree name repo@<sha> in the current directory
            name = "@".join([self.repository_name, ref_commit])

        return self.run_command("worktree", "add", name, ref_commit)

    def remove_worktree(self, commit_or_tag: str, force: bool = False):
        if not any(commit_or_tag in wt for wt in self.worktrees):
            msg = f"fatal: Worktree with ID {commit_or_tag} does not exist."
            return msg

        try:
            worktree_to_delete = next(wt for wt in self.worktrees if commit_or_tag in wt)
        except StopIteration:
            raise ValueError(f"no worktree with ID {commit_or_tag} found.")

        self.worktrees.remove(worktree_to_delete)
        return self.run_command("worktree", "remove", commit_or_tag,
                                force=force)
