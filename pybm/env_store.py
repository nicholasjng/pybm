import datetime
from pathlib import Path
from typing import List, Any, Optional, Union

import yaml

from pybm import PybmConfig
from pybm.exceptions import PybmError
from pybm.git import GitWorktreeWrapper
from pybm.specs import Worktree, PythonSpec, BenchmarkEnvironment
from pybm.util.common import lmap
from pybm.util.git import disambiguate_info


class EnvironmentStore:
    """Environment context manager keeping track of the present benchmarking
    environments."""

    def __init__(self,
                 path: Union[str, Path],
                 verbose: bool = False,
                 missing_ok: bool = False):
        self.config = PybmConfig.load(path=path)
        self.git: GitWorktreeWrapper = GitWorktreeWrapper(config=self.config)
        self.env_file = Path(self.config.get_value("core.envFile"))
        self.verbose = verbose
        self.missing_ok = missing_ok
        self.environments: List[BenchmarkEnvironment] = []

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    def load(self):
        # silence warning during `pybm init` specifically
        if not self.env_file.exists():
            if not self.missing_ok:
                print("Warning: No environment configuration file found. "
                      "To create a configuration file and discover "
                      "existing environments, run `pybm init` "
                      "from the root of your git repository.")
        else:
            if self.verbose:
                print("Loading benchmark environments from disk at location "
                      f"{self.env_file}.....", end="")
            with open(self.env_file, "r") as cfg:
                envs = yaml.load(cfg, Loader=yaml.FullLoader)
            if self.verbose:
                print("done.")
            self.environments = lmap(BenchmarkEnvironment.from_dict, envs)

    def save(self):
        envs = lmap(lambda x: x.to_dict(), self.environments)
        if self.verbose:
            print(f"Saving benchmark environments to disk at location "
                  f"{self.env_file}.....", end="")
        with open(self.env_file, "w") as cfg:
            yaml.dump(envs, cfg)
        if self.verbose:
            print("done.")

    def create(self, name: Optional[str], worktree: Worktree,
               python: PythonSpec, created: str) -> BenchmarkEnvironment:
        name = name or f"env_{len(self.environments) + 1}"
        print(f"Creating benchmark environment {name!r}.....", end="")
        env = BenchmarkEnvironment(name=name,
                                   worktree=worktree,
                                   python=python,
                                   created=created,
                                   last_modified=created)
        print("done.")
        self.environments.append(env)
        return env

    def delete(self, env: BenchmarkEnvironment) -> BenchmarkEnvironment:
        self.environments.remove(env)
        return env

    def get(self, value: Any) -> BenchmarkEnvironment:
        # check for known git info, otherwise use name
        info = disambiguate_info(value)
        if info is not None:
            attr = "worktree." + info
        else:
            attr = "name"
        if self.verbose:
            print(f"Attempting to match benchmark environment with "
                  f"{attr.replace('.', ' ')} {value!r}.....", end="")
        try:
            if info is not None:
                env = next(
                    e for e in self.environments if e.worktree ==
                    self.git.get_worktree_by_attr(info, value)
                )
            else:
                env = next(
                    e for e in self.environments if e.name == value
                )
            if self.verbose:
                print("success.")
            return env
        except StopIteration:
            if self.verbose:
                print("failed")
            raise PybmError(f"No benchmark environment found with "
                            f"{attr.replace('.', ' ')} {value!r}.")

    def update(self, name: str, attr: str, value: Any) -> None:
        # TODO: Only some values (e.g. linked venv, worktree branch) make
        #  sense to update. Filter by admissible updates with a handler
        #  scheme
        env_to_update = self.delete(name)
        env_to_update.set_value(attr=attr, value=value)
        env_to_update.set_value("last_modified", str(datetime.datetime.now()))
        self.environments.append(env_to_update)
