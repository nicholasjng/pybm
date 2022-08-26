from pathlib import Path
from typing import Optional, Tuple, Union

from pybm.exceptions import GitError
from pybm.git import GitWorktree
from pybm.util.formatting import abbrev_home
from pybm.util.git import checkout, disambiguate_info, resolve_commit
from pybm.util.subprocess import run_subprocess
from pybm.util.venv import get_executable, get_venv_root
from pybm.venv import PythonVenv

_MAIN_NAME = "main"


class Workspace:
    """
    Class representing a pybm workspace, consisting of a git worktree and a
    provided Python environment for benchmarking.
    """

    def __init__(self, name: str, worktree: GitWorktree, venv: PythonVenv):
        # name to reference from the command line
        self.name = name

        self.worktree = worktree

        # git worktree information
        self.root = worktree.root
        self.commit = worktree.commit
        self.branch = worktree.branch
        self.tag = worktree.tag

        self.venv = venv

        # Python virtual environment configuration
        self.executable = venv.executable
        self.version = venv.version
        self.packages = venv.packages
        self.locations = venv.locations

    @classmethod
    def deserialize(cls, obj):
        name = obj["name"]
        root = obj["root"]
        commit = obj["commit"]
        branch = obj["branch"]
        tag = obj["tag"]

        worktree = GitWorktree(root=root, commit=commit, branch=branch, tag=tag)

        executable = obj["executable"]
        directory = get_venv_root(executable)
        version = obj["version"]

        venv = PythonVenv(
            directory=directory, executable=executable, version=version
        ).update()

        return Workspace(name=name, worktree=worktree, venv=venv)

    def clean(self):
        command = ["git", "clean", "-fd"]
        run_subprocess(command=command, cwd=self.root)

    def get_ref_and_type(self) -> Tuple[str, str]:
        if self.branch is not None:
            return self.branch, "branch"
        elif self.tag is not None:
            return self.tag, "tag"
        else:  # commit is always not None
            return self.commit, "commit"

    def has_untracked_files(self):
        """Check whether a git worktree has untracked files."""
        command = ["git", "ls-files", "--others", "--exclude-standard"]
        _, output = run_subprocess(command=command, ex_type=GitError, cwd=self.root)
        return output != ""

    def link(self, directory: Union[str, Path]):
        executable = get_executable(directory)
        venv = PythonVenv(directory=directory, executable=executable).update()

        self.executable = executable
        self.packages = venv.packages
        self.locations = venv.locations
        self.venv = venv

    def serialize(self):
        obj = self.__dict__

        obj.pop("worktree")
        obj.pop("venv")

        return obj

    def switch(self, ref: str, ref_type: Optional[str] = None):
        old_ref, old_type = self.get_ref_and_type()

        if not ref_type:
            ref_type = disambiguate_info(ref)

        if ref_type not in ["commit", "branch", "tag"]:
            raise GitError(
                f"Failed to switch checkout of worktree {abbrev_home(self.root)}: "
                f"Object {ref!r} could not be interpreted as a valid git reference."
            )

        checkout(ref=ref, cwd=self.root)

        # null the old reference type if necessary
        if ref_type != old_type:
            self.__setattr__(old_type, None)

        self.__setattr__(ref_type, ref)

        self.commit = resolve_commit(ref)

    def venv_in_tree(self):
        venv_root = get_venv_root(self.executable)
        if not venv_root.exists():
            return False
        else:
            return venv_root.parent == Path(self.root)
