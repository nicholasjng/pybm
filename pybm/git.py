"""Small Git wrapper for operating on a repository via Python."""

import subprocess
from typing import Optional

class GitWrapper:
    """Wrapper class for a Git-based benchmark environment creator."""
    def __init__(self):
        # TODO: Grab existing worktrees directly from git worktree list
        self.worktree_ids = []
        self.executable = "git"

    def run_command(self, command: str, subcommand: Optional[str] = None,
                    *args, **kwargs):
        call_args = [self.executable, command]
        if subcommand:
            call_args.append(subcommand)

        call_args += list(args)

        # TODO: Handle kwargs as additional command line args to git
        return subprocess.check_output(args)

    def list_worktrees(self):
        return self.run_command("worktree", "list")

    def add_worktree(self, commit_or_tag: str, **kwargs):
        if commit_or_tag in self.worktree_ids:
            msg = f"fatal: Worktree with ID {commit_or_tag} already exists."
            return msg

        self.worktree_ids.append(commit_or_tag)
        # TODO: Distinguish between tags and commits
        return self.run_command("worktree", "add", commit_or_tag)

    def remove_worktree(self, commit_or_tag: str):
        if commit_or_tag not in self.worktree_ids:
            msg = f"fatal: Worktree with ID {commit_or_tag} does not exist."
            return msg

        self.worktree_ids.remove(commit_or_tag)
        # TODO: Distinguish between tags and commits
        # TODO 2: Clean up worktrees before deletion, e.g. by
        #  using --force, but ideally less violently. This is important e.g.
        #  when creating a custom requirements venv inside the worktree

        return self.run_command("worktree", "remove", commit_or_tag)
