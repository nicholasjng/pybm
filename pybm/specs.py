import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple, Union

from pybm.util.git import map_commits_to_tags
from pybm.mixins import StateMixin

ConfigValue = Union[str, int, float]


@dataclass(frozen=True)
class PythonSpec:
    """Dataclass representing a Python virtual environment specification."""
    root: str = field()
    executable: str = field()
    version: str = field()
    packages: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)


@dataclass
class Worktree:
    """Dataclass representing a git worktree specification."""
    root: str
    commit: str
    branch: Optional[str]
    tag: Optional[str]

    @classmethod
    def from_list(cls, wt_info: List[str]):
        root, commit, branch = wt_info
        branch_id = branch if branch != "detached" else None
        commit_tag_mapping = map_commits_to_tags()
        tag = commit_tag_mapping.get(commit, None)
        return Worktree(root=root, branch=branch_id, commit=commit, tag=tag)

    def get_ref_and_type(self, bare: bool = False) -> Tuple[str, str]:
        # at most two of commit, branch, tag are not None
        # bare mode = only return the name, not the git refs/... prefix
        if self.branch is not None:
            branch = self.branch.split("/")[-1] if bare else self.branch
            return branch, "branch"
        elif self.tag is not None:
            tag = self.tag.split("/")[-1] if bare else self.tag
            return tag, "tag"
        else:
            return self.commit, "commit"


@dataclass(unsafe_hash=True)
class BenchmarkEnvironment(StateMixin):
    """Dataclass representing a benchmarking environment configuration."""
    name: str
    worktree: Worktree
    python: PythonSpec
    created: str
    last_modified: str

    @classmethod
    def from_dict(cls, spec: Dict[str, Any]):
        return BenchmarkEnvironment(name=spec["name"],
                                    worktree=Worktree(**spec["worktree"]),
                                    python=PythonSpec(**spec["python"]),
                                    created=spec["created"],
                                    last_modified=spec["last_modified"])

    def to_dict(self):
        return {"name": self.name,
                "worktree": asdict(self.worktree),
                "python": asdict(self.python),
                "created": self.created,
                "last_modified": self.last_modified}


@dataclass
class CoreGroup:
    logFile: str = "logs/logs.txt"
    defaultLevel: int = logging.DEBUG
    loggingFormatter: str = "%(asctime)s — %(name)-12s " \
                            "— %(levelname)s — %(message)s"
    datetimeFormatter: str = "%d/%m/%Y, %H:%M:%S"


@dataclass
class GitGroup:
    createWorktreeInParentDirectory: bool = True


@dataclass
class RunnerGroup:
    className: str = "pybm.runners.TimeitRunner"
    resultDirectory: str = "results"
    failFast: bool = False
    numRepetitions: int = 1
    contextProviders: str = ""
    GoogleBenchmarkWithRandomInterleaving: bool = True
    GoogleBenchmarkSaveAggregatesOnly: bool = True


@dataclass
class BuilderGroup:
    className: str = "pybm.builders.StdlibBuilder"
    homeDirectory: str = ""
    localWheelCaches: str = ""
    persistentVenvOptions: str = ""
    persistentPipInstallOptions: str = ""
    persistentPipUninstallOptions: str = ""


@dataclass
class ReporterGroup:
    className: str = "pybm.reporters.JSONReporter"
    resultDirectory: str = "results"
    targetTimeUnit: str = "usec"
    significantDigits: int = 2
