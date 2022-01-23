import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple

from pybm.exceptions import GitError
from pybm.mixins import StateMixin
from pybm.util.git import map_commits_to_tags
from pybm.util.subprocess import run_subprocess


@dataclass(frozen=True)
class PythonSpec:
    """Dataclass representing a Python virtual environment."""

    root: str = field()
    executable: str = field()
    version: str = field()
    packages: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)

    def update_packages(self, packages: List[str]):
        self.packages.clear()
        self.packages.extend(packages)


@dataclass
class Worktree:
    """Dataclass representing a git worktree."""

    root: str
    commit: str
    branch: Optional[str] = None
    tag: Optional[str] = None

    @classmethod
    def from_list(cls, wt_info: List[str]):
        root, commit, branch_name = wt_info

        if branch_name == "detached":
            branch = None
        else:
            branch = branch_name.replace("refs/heads/", "")

        commit_tag_mapping = map_commits_to_tags()

        tag = commit_tag_mapping.get(commit, None)

        return Worktree(root=root, branch=branch, commit=commit, tag=tag)

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

    def clean(self):
        command = ["git", "clean", "-fd"]
        run_subprocess(command=command, cwd=self.root)


@dataclass(unsafe_hash=True)
class BenchmarkEnvironment(StateMixin):
    """Dataclass representing a benchmarking environment configuration."""

    name: str
    worktree: Worktree
    python: PythonSpec
    created: str
    lastmod: str

    @classmethod
    def from_dict(cls, name: str, spec: Dict[str, Any]):
        return BenchmarkEnvironment(
            name=name,
            worktree=Worktree(**spec["worktree"]),
            python=PythonSpec(**spec["python"]),
            created=spec["created"],
            lastmod=spec["lastmod"],
        )

    def to_dict(self):
        return {
            "name": self.name,
            "worktree": asdict(self.worktree),
            "python": asdict(self.python),
            "created": self.created,
            "lastmod": self.lastmod,
        }


@dataclass
class CoreGroup:
    datefmt: str = "%d/%m/%Y, %H:%M:%S"
    envfile: str = ".pybm/envs.toml"
    logfile: str = "logs/logs.txt"
    logfmt: str = "%(asctime)s — %(name)-12s " "— %(levelname)s — %(message)s"
    loglevel: int = logging.DEBUG
    resultdir: str = "results"


@dataclass
class GitGroup:
    basedir: str = ".."
    legacycheckout: bool = False


@dataclass
class BuilderGroup:
    name: str = "pybm.builders.VenvBuilder"
    homedir: str = ""
    wheelcaches: str = ""
    venvoptions: str = ""
    pipinstalloptions: str = ""
    pipuninstalloptions: str = ""


@dataclass
class RunnerGroup:
    name: str = "pybm.runners.TimeitRunner"
    failfast: bool = False
    contextproviders: str = ""


@dataclass
class ReporterGroup:
    name: str = "pybm.reporters.ConsoleReporter"
    timeunit: str = "usec"
    significantdigits: int = 2


EmptyPythonSpec = PythonSpec(root="", executable="", version="")
