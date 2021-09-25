import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple, Union

from pybm import __version__ as current_pybm_version
from pybm.util.git import map_commits_to_tags
from pybm.mixins import StateMixin

ConfigValue = Union[str, int, float]


@dataclass
class EnvSpec:
    """Dataclass representing a Python virtual environment specification."""
    root: str = field()
    executable: str = field()
    python_version: str = field()
    packages: List[str] = field(default_factory=list)


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

    def get_ref_and_type(self) -> Tuple[str, str]:
        # at most two of commit, branch, tag are not None
        if self.branch is not None:
            return self.branch, "branch"
        elif self.tag is not None:
            return self.tag, "tag"
        else:
            return self.commit, "commit"


@dataclass(unsafe_hash=True)
class BenchmarkEnvironment(StateMixin):
    """Dataclass representing a benchmarking environment configuration."""
    name: str
    workspace: Worktree
    venv: EnvSpec
    created: str
    last_modified: str

    @classmethod
    def from_dict(cls, spec: Dict[str, Any]):
        return BenchmarkEnvironment(name=spec["name"],
                                    workspace=Worktree(**spec["workspace"]),
                                    venv=EnvSpec(**spec["venv"]),
                                    created=spec["created"],
                                    last_modified=spec["last_modified"])

    def to_dict(self):
        return {"name": self.name,
                "workspace": asdict(self.workspace),
                "venv": asdict(self.venv),
                "created": self.created,
                "last_modified": self.last_modified}


@dataclass
class CoreGroup:
    version: str = current_pybm_version
    logFile: str = "logs/logs.txt"
    defaultLevel: int = logging.DEBUG
    loggingFormatter: str = "%(asctime)s — %(name)-12s " \
                            "— %(levelname)s — %(message)s"
    datetimeFormatter: str = "%d/%m/%Y, %H:%M:%S"


@dataclass
class RunnerGroup:
    className: str = "pybm.runners.GoogleBenchmarkRunner"
    resultDirectory: str = "results"
    failFast: bool = False
    contextProviders: str = ""
    GoogleBenchmarkWithRandomInterleaving: bool = True
    GoogleBenchmarkNumRepetitions: int = 0
    GoogleBenchmarkSaveAggregatesOnly: bool = True


@dataclass
class WorkspaceGroup:
    createInParentDirectory: bool = True


@dataclass
class BuilderGroup:
    className: str = "pybm.builders.PythonStdlibBuilder"
    homeDirectory: str = ""
    localWheelCaches: str = ""
    persistentVenvOptions: str = ""
    persistentPipInstallOptions: str = ""
    persistentPipUninstallOptions: str = ""


@dataclass
class ReporterGroup:
    pass
