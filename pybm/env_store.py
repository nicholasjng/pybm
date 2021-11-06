import argparse
import sys
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from typing import List, Any

import yaml

from pybm import PybmConfig
from pybm.builders.base import PythonEnvBuilder
from pybm.builders.util import is_valid_venv
from pybm.config import get_builder_class, get_runner_requirements
from pybm.exceptions import PybmError
from pybm.git import GitWorktreeWrapper
from pybm.specs import Worktree, PythonSpec, BenchmarkEnvironment
from pybm.util.common import lmap
from pybm.util.git import disambiguate_info, is_main_worktree
from pybm.util.print import (
    abbrev_home,
    calculate_column_widths,
    make_line,
    make_separator,
)


def cleanup_venv(builder, worktree: Worktree, spec: PythonSpec):
    print("Cleaning up venv after exception.")
    # venv is not linked
    if Path(spec.root).parent == Path(worktree.root):
        builder.delete(spec.root)
    else:
        print(f"Did not tear down linked venv with root {spec.root}.")


def cleanup_worktree(git_worktree: GitWorktreeWrapper, worktree: Worktree):
    print("Cleaning up created worktree after exception.")
    git_worktree.remove(info=worktree.root)


class EnvironmentStore:
    """Environment context manager keeping track of the present benchmarking
    environments."""

    def __init__(
        self, config: PybmConfig, verbose: bool = False, missing_ok: bool = False
    ):
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
                print(
                    "Warning: No environment configuration file found. "
                    "To create a configuration file and discover "
                    "existing environments, run `pybm init` "
                    "from the root of your git repository."
                )
        else:
            if self.verbose:
                print(
                    f"Loading benchmark environments from file {self.env_file}.....",
                    end="",
                )

            with open(self.env_file, "r") as cfg:
                envs = yaml.load(cfg, Loader=yaml.FullLoader)

            if self.verbose:
                print("done.")

            self.environments = lmap(BenchmarkEnvironment.from_dict, envs)

    def save(self):
        envs = lmap(lambda x: x.to_dict(), self.environments)

        if self.verbose:
            print(
                f"Saving benchmark environments to file {self.env_file}.....",
                end="",
            )

        with open(self.env_file, "w") as cfg:
            yaml.dump(envs, cfg)

        if self.verbose:
            print("done.")

    def create(self, options: argparse.Namespace) -> BenchmarkEnvironment:
        git_worktree: GitWorktreeWrapper = GitWorktreeWrapper(config=self.config)
        builder: PythonEnvBuilder = get_builder_class(config=self.config)

        commit_ish = options.commit_ish

        print(f"Creating benchmark environment for git ref {commit_ish!r}.")

        with ExitStack() as ctx:
            worktree = git_worktree.add(
                commit_ish=commit_ish,
                destination=options.destination,
                force=options.force,
                checkout=not options.no_checkout,
                resolve_commits=options.resolve_commits,
            )

            ctx.callback(cleanup_worktree, git_worktree, worktree)

            if options.link_dir is None:
                python_spec = builder.create(
                    options.python_executable,
                    destination=Path(worktree.root) / "venv",
                    options=options.venv_options,
                )
            else:
                python_spec = builder.link(options.link_dir)

            ctx.callback(cleanup_venv, builder, worktree, python_spec)

            # installing runner requirements and pybm
            required = get_runner_requirements(config=self.config)
            required.append("git+https://github.com/nicholasjng/pybm")

            builder.install_packages(
                spec=python_spec, packages=required, verbose=self.verbose
            )

            if worktree is not None and python_spec is not None:
                # pop all cleanups and re-push env YAML save
                ctx.pop_all()
                ctx.callback(self.save)

            name = options.name or f"env_{len(self.environments) + 1}"

            created = datetime.now().strftime(self.fmt)

            environment = BenchmarkEnvironment(
                name=name,
                worktree=worktree,
                python=python_spec,
                created=created,
                last_modified=created,
            )

            self.environments.append(environment)

            print(f"Successfully created benchmark environment for ref {commit_ish!r}.")

        return environment

    def delete(self, options: argparse.Namespace) -> BenchmarkEnvironment:
        builder: PythonEnvBuilder = get_builder_class(config=self.config)
        git_worktree: GitWorktreeWrapper = GitWorktreeWrapper(config=self.config)

        with ExitStack() as ctx:
            ctx.callback(self.save)

            env_to_remove = self.get(options.identifier)
            env_name = env_to_remove.name

            print(
                f"Found matching benchmark environment {env_name!r}, "
                "starting removal."
            )

            venv_root = Path(env_to_remove.get_value("python.root"))
            worktree_root = Path(env_to_remove.get_value("worktree.root"))

            # Remove venv first if inside the worktree to avoid git problems
            if venv_root.exists() and venv_root.parent == worktree_root:
                builder.delete(venv_root)

            git_worktree.remove(str(worktree_root), force=options.force)

            self.environments.remove(env_to_remove)

            print(f"Successfully removed benchmark environment {env_name!r}.")

        return env_to_remove

    def get(self, value: Any) -> BenchmarkEnvironment:
        git_worktree: GitWorktreeWrapper = GitWorktreeWrapper(config=self.config)

        # check for known git info, otherwise use name
        info = disambiguate_info(value)
        attr = "worktree " + info if info else "name"

        if self.verbose:
            print(f"Matching benchmark environment with {attr} {value!r}.....", end="")
        try:
            if info is not None:
                env = next(
                    e
                    for e in self.environments
                    if e.worktree == git_worktree.get_worktree_by_attr(info, value)
                )
            else:
                env = next(e for e in self.environments if e.name == value)

            if self.verbose:
                print("success.")

            return env
        except StopIteration:
            if self.verbose:
                print("failed.")

            raise PybmError(
                f"Benchmark environment with {attr} {value!r} does not exist."
            )

    def list(self, padding: int = 1):
        column_names = [
            "Name",
            "Git Reference",
            "Reference type",
            "Worktree directory",
            "Python version",
        ]

        env_data = [column_names]
        for env in self.environments:
            values = [env.get_value("name")]
            values.extend(env.worktree.get_ref_and_type())
            root: str = env.get_value("worktree.root")
            values.append(abbrev_home(root))
            values.append(env.get_value("python.version"))
            env_data.append(values)

        column_widths = calculate_column_widths(env_data)

        for i, d in enumerate(env_data):
            print(make_line(d, column_widths, padding=padding))
            if i == 0:
                print(make_separator(column_widths, padding=padding))

    def sync(self):
        builder: PythonEnvBuilder = get_builder_class(config=self.config)
        git_worktree: GitWorktreeWrapper = GitWorktreeWrapper(config=self.config)

        with ExitStack() as ctx:
            ctx.callback(self.save)
            for i, worktree in enumerate(git_worktree.list()):
                venv_root = Path(worktree.root) / "venv"

                if venv_root.exists() and is_valid_venv(
                    venv_root, verbose=self.verbose
                ):
                    python_spec = builder.link(venv_root, verbose=self.verbose)
                else:
                    # TODO: Enable auto-grabbing from venv home
                    python_spec = builder.create(sys.executable, venv_root)

                created = datetime.now().strftime(self.fmt)

                name = "root" if is_main_worktree(worktree.root) else f"env_{i + 1}"

                env = BenchmarkEnvironment(
                    name=name,
                    worktree=worktree,
                    python=python_spec,
                    created=created,
                    last_modified=created,
                )

                self.environments.append(env)

    def switch(self, name: str, ref: str) -> BenchmarkEnvironment:
        git_worktree: GitWorktreeWrapper = GitWorktreeWrapper(config=self.config)

        ref_type = disambiguate_info(ref)

        with ExitStack() as ctx:
            ctx.callback(self.save)

            env = self.get(name)

            if self.verbose:
                print(
                    f"Switching checkout of environment {env.name!r} to "
                    f"{ref_type} {ref!r}."
                )

            worktree = git_worktree.switch(
                worktree=env.worktree, ref=ref, ref_type=ref_type
            )

            env.worktree = worktree

        return env
