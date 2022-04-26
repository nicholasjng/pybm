from typing import Tuple, Optional, List

from pybm.exceptions import GitError
from pybm.git import GitWorktree
from pybm.specs import PythonSpec
from pybm.util.git import disambiguate_info, checkout, resolve_commit
from pybm.util.formatting import abbrev_home
from pybm.util.subprocess import run_subprocess


_MAIN_NAME = "main"


class Workspace:
    """
    Class representing a pybm workspace, consisting of a git worktree and a
    provided Python environment for benchmarking.
    """

    def __init__(self, name: str, worktree: GitWorktree, spec: PythonSpec):
        # name to reference from the command line
        self.name = name

        # git worktree information
        self.root = worktree.root
        self.commit = worktree.commit
        self.branch = worktree.branch
        self.tag = worktree.tag

        # Python virtual environment configuration
        self.executable = spec.executable
        self.version = spec.version
        self.packages = spec.packages
        self.locations = spec.locations

    @classmethod
    def from_dict(cls, info):
        name = info["name"]

        root = info["root"]
        commit = info["commit"]
        branch = info["branch"]
        tag = info["tag"]

        worktree = GitWorktree(root=root, commit=commit, branch=branch, tag=tag)

        executable = info["executable"]
        version = info["version"]
        packages = info["packages"]
        locations = info["locations"]

        spec = PythonSpec(
            executable=executable,
            version=version,
            packages=packages,
            locations=locations,
        )

        return Workspace(name=name, worktree=worktree, spec=spec)

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

    def get_spec(self) -> PythonSpec:
        return PythonSpec(
            executable=self.executable,
            version=self.version,
            packages=self.packages,
            locations=self.locations,
        )

    def has_untracked_files(self):
        """Check whether a git worktree has untracked files."""
        command = ["git", "ls-files", "--others", "--exclude-standard"]
        _, output = run_subprocess(command=command, ex_type=GitError, cwd=self.root)
        return output != ""

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

    def list(self) -> Tuple[List[str], List[str]]:
        if self.executable == "":
            return [], []

        command = [self.executable, "-m", "pip", "list"]

        rc, pip_output = run_subprocess(command)

        # split off table header, separator from `pip list` output
        flat_pkg_table = pip_output.splitlines()[2:]
        packages, locations = [], []

        for line in flat_pkg_table:
            # TODO: When using pybm.Packages here, change to --format=json to parse
            #  directly
            package, version, *loc = line.split()[:2]
            packages.append("==".join((package, version)))
            if loc:
                locations.append(":".join((package, *loc)))

        return packages, locations

    def update_packages(self):
        self.packages, self.locations = self.list()
        return self
