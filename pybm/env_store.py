import argparse
import sys
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from typing import List, Any

import yaml

from pybm import PybmConfig
from pybm.builders.base import PythonEnvBuilder
from pybm.config import get_builder_class, get_runner_requirements
from pybm.exceptions import PybmError
from pybm.git import GitWorktreeWrapper
from pybm.specs import Worktree, PythonSpec, BenchmarkEnvironment
from pybm.util.common import lmap
from pybm.util.git import disambiguate_info
from pybm.util.print import format_environments


def cleanup_venv(builder, worktree: Worktree, spec: PythonSpec):
    print("Cleaning up venv after exception.")
    # venv is not linked
    if Path(spec.root).parent == Path(worktree.root):
        builder.delete(spec.root)
    else:
        print(f"Did not tear down linked venv with root {spec.root}")


def cleanup_worktree(git: GitWorktreeWrapper, worktree: Worktree):
    print("Cleaning up created worktree after exception.")
    git.remove_worktree(info=worktree.root)


class EnvironmentStore:
    """Environment context manager keeping track of the present benchmarking
    environments."""

    def __init__(self,
                 config: PybmConfig,
                 verbose: bool = False,
                 missing_ok: bool = False):
        self.config = config
        self.env_file = Path(self.config.get_value("core.envFile"))
        self.fmt = self.config.get_value("core.datetimeFormatter")
        self.verbose = verbose
        self.missing_ok = missing_ok

        self.environments: List[BenchmarkEnvironment] = []
        self.load()

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

    def create(self, options: argparse.Namespace) -> BenchmarkEnvironment:
        git: GitWorktreeWrapper = GitWorktreeWrapper(config=self.config)
        builder: PythonEnvBuilder = get_builder_class(config=self.config)

        commit_ish = options.commit_ish

        print(f"Creating benchmark environment for git ref "
              f"{commit_ish!r}.")
        with ExitStack() as create_context:
            worktree = git.add_worktree(
                commit_ish=commit_ish,
                destination=options.destination,
                force=options.force,
                checkout=not options.no_checkout,
                resolve_commits=options.resolve_commits)

            create_context.callback(cleanup_worktree, git, worktree)

            if options.link_dir is None:
                python_spec = builder.create(
                    options.python_executable,
                    destination=Path(worktree.root) / "venv",
                    options=options.venv_options)
            else:
                python_spec = builder.link_existing(options.link_dir)

            create_context.callback(cleanup_venv, builder, worktree,
                                    python_spec)

            # installing runner requirements and pybm
            required = get_runner_requirements(config=self.config)
            required.append("git+https://github.com/nicholasjng/pybm")
            builder.install_packages(
                spec=python_spec,
                packages=required,
                verbose=self.verbose)

            if worktree is not None and python_spec is not None:
                # pop all cleanups and re-push env YAML save
                create_context.pop_all()
                create_context.callback(self.save)

            name = options.name or f"env_{len(self.environments) + 1}"

            created = datetime.now().strftime(self.fmt)
            environment = BenchmarkEnvironment(
                name=name,
                worktree=worktree,
                python=python_spec,
                created=created,
                last_modified=created)
            self.environments.append(environment)
            print(f"Successfully created benchmark environment for ref "
                  f"{commit_ish!r}.")

        return environment

    def delete(self, options: argparse.Namespace) -> BenchmarkEnvironment:
        builder: PythonEnvBuilder = get_builder_class(config=self.config)
        git: GitWorktreeWrapper = GitWorktreeWrapper(config=self.config)

        with ExitStack() as delete_context:
            delete_context.callback(self.save)

            env_to_remove = self.get(options.identifier)
            env_name = env_to_remove.name
            print(f"Found matching benchmark environment {env_name!r}, "
                  "starting removal.")

            # Remove venv first LIFO style to avoid git problems, if located
            # inside the worktree
            venv_root = Path(env_to_remove.get_value("python.root"))
            worktree_root = Path(env_to_remove.get_value("worktree.root"))
            if venv_root.exists() and venv_root.parent == worktree_root:
                builder.delete(venv_root)

            git.remove_worktree(env_to_remove.get_value("worktree.root"),
                                force=options.force)

            self.environments.remove(env_to_remove)
            print(f"Successfully removed benchmark environment "
                  f"{env_name!r}.")

        return env_to_remove

    def get(self, value: Any) -> BenchmarkEnvironment:
        git: GitWorktreeWrapper = GitWorktreeWrapper(config=self.config)

        # check for known git info, otherwise use name
        info = disambiguate_info(value)
        if info is not None:
            attr = "worktree " + info
        else:
            attr = "name"
        if self.verbose:
            print(f"Matching benchmark environment with {attr} "
                  f"{value!r}.....", end="")
        try:
            if info is not None:
                env = next(
                    e for e in self.environments if e.worktree ==
                    git.get_worktree_by_attr(info, value))
            else:
                env = next(
                    e for e in self.environments if e.name == value)
            if self.verbose:
                print("success.")
            return env
        except StopIteration:
            if self.verbose:
                print("failed.")
            raise PybmError(f"No benchmark environment found with "
                            f"{attr} {value!r}.")

    def list(self):
        format_environments(self.environments)

    def sync(self):
        builder: PythonEnvBuilder = get_builder_class(config=self.config)
        git: GitWorktreeWrapper = GitWorktreeWrapper(config=self.config)

        with ExitStack() as sync:
            sync.callback(self.save)
            for i, worktree in enumerate(git.list_worktrees()):
                venv_root = Path(worktree.root) / "venv"
                if venv_root.exists() and venv_root.is_dir():
                    python_spec = builder.link_existing(venv_root,
                                                        verbose=self.verbose)
                else:
                    python_spec = builder.create(sys.executable, venv_root)
                    # TODO: Enable auto-grabbing from venv home
                created = datetime.now().strftime(self.fmt)

                # TODO: Assert that the main worktree is "root"
                env = BenchmarkEnvironment(
                    name="root" if i == 0 else f"env_{i + 1}",
                    worktree=worktree,
                    python=python_spec,
                    created=created,
                    last_modified=created
                )
                self.environments.append(env)

    def update(self, name: str, attr: str, value: Any) -> None:
        pass
        # TODO: Only some values (e.g. linked venv, worktree branch) make
        #  sense to update. Filter by admissible updates with a handler
        #  scheme
        # env_to_update = self.delete(name)
        # env_to_update.set_value(attr=attr, value=value)
        # env_to_update.set_value(
        #     "last_modified", datetime.now().strftime(self.fmt)
        # )
        # self.environments.append(env_to_update)
