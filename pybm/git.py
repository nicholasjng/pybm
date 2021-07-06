"""Small Git wrapper for operating on a repository via Python."""

import subprocess
import re
from typing import Optional, Tuple, List, Dict
from git_utils import parse_flags

_ROOT = "root"
_COMMIT = "commit"
_BRANCH = "branch"

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
        # parse git command line args separately
        call_args += parse_flags(command, subcommand, **kwargs)
        return subprocess.check_output(call_args).decode("utf-8")

    def get_version(self) -> Tuple[int]:
        output = self.run_command("--version")
        version_string = re.search(r'([\d.]+)', output).group()
        version_ints = map(int, version_string.split("."))
        return tuple(version_ints)

    def get_worktree_by_attribute(self, key: str, attr: str):
        try:
            wt = next(wt for wt in self.worktrees if wt[key] == attr)
        except KeyError:
            raise ValueError(f"Worktree attribute {key} does not exist.")
        except StopIteration:
            wt = None
        return wt

    def list_worktrees(self) -> List[Dict[str, str]]:
        worktree_string = self.run_command("worktree", "list")
        worktree_lists = map(str.split, worktree_string.splitlines())
        # order of listed git worktree data
        keys = [_ROOT, _COMMIT, _BRANCH]
        worktree_dicts = map(lambda x: dict(zip(keys, x)), worktree_lists)
        return list(worktree_dicts)

    # TODO: Cache list of tags (?)
    def list_tags(self):
        return self.run_command("tag").splitlines()

    def add_worktree(self, commit_or_tag: str, name: Optional[str] = None,
                     force=False, checkout=False, lock=False):
        # TODO: Allow multiple worktrees of the same commit
        #  for different custom requirements
        if self.get_worktree_by_attribute(_COMMIT, commit_or_tag):
            msg = f"fatal: Worktree with ID {commit_or_tag} already exists."
            return msg
        # ID is a tag
        if commit_or_tag in self.list_tags():
            # use tags/$TAG syntax to avoid ambiguity
            ref_commit = self.run_command("rev-list", None, "-n", "1",
                                          f"tags/{commit_or_tag}")
        # ID is a commit SHA
        else:
            ref_commit = commit_or_tag

        if not name:
            # worktree name repo@<sha> in the current directory
            name = "@".join([self.repository_name, ref_commit])

        return self.run_command("worktree", "add", name, ref_commit,
                                force=force, checkout=checkout, lock=lock)

    def remove_worktree(self, commit_or_tag: str, force=False):
        # find worktree by commit or tag
        rm_worktree = self.get_worktree_by_attribute(_COMMIT, commit_or_tag)
        if not rm_worktree:
            msg = f"fatal: Worktree with ID {commit_or_tag} does not exist."
            return msg

        self.worktrees.remove(rm_worktree)
        return self.run_command("worktree", "remove", commit_or_tag,
                                force=force)
