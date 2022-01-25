import sys
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict

import toml

from pybm import PybmConfig
from pybm.builders import BaseBuilder
from pybm.config import get_component_class, get_runner_requirements
from pybm.exceptions import PybmError
from pybm.git import GitWorktreeWrapper
from pybm.specs import Worktree, PythonSpec, BenchmarkEnvironment
from pybm.util.common import dvmap
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

        # git worktree wrapper and builder class
        self.git_worktree: GitWorktreeWrapper = GitWorktreeWrapper(config=self.config)
        self.builder: BaseBuilder = get_component_class("builder", config=self.config)

        # relevant config attributes
        self.env_file = Path(self.config.get_value("core.envfile"))
        self.fmt = self.config.get_value("core.datefmt")

        # attributes controlling print behavior
        self.verbose = verbose
        self.missing_ok = missing_ok

        self.environments: Dict[str, BenchmarkEnvironment] = {}
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
                envs = toml.load(cfg)

            if self.verbose:
                print("done.")

            for name, info in envs.items():
                self.environments[name] = BenchmarkEnvironment.from_dict(name, info)

    def save(self):
        envs = dvmap(lambda x: x.to_dict(), self.environments)

        if self.verbose:
            print(
                f"Saving benchmark environments to file {self.env_file}.....",
                end="",
            )

        with open(self.env_file, "w") as cfg:
            toml.dump(envs, cfg)

        if self.verbose:
            print("done.")

    def create(
        self,
        commit_ish: str,
        name: str,
        destination: str,
        force: bool,
        checkout: bool,
        resolve_commits: bool,
        link_dir: Optional[str],
        **builder_kwargs,
    ) -> BenchmarkEnvironment:
        print(f"Creating benchmark environment for git ref {commit_ish!r}.")

        with ExitStack() as ctx:
            worktree = self.git_worktree.add(
                commit_ish=commit_ish,
                destination=destination,
                force=force,
                checkout=checkout,
                resolve_commits=resolve_commits,
            )

            ctx.callback(cleanup_worktree, self.git_worktree, worktree)

            if link_dir is None:
                python_spec = self.builder.create(
                    destination=Path(worktree.root) / "venv",
                    **builder_kwargs,
                )
            else:
                python_spec = self.builder.link(link_dir)

            ctx.callback(cleanup_venv, self.builder, worktree, python_spec)

            # install runner requirements
            self.builder.install(
                spec=python_spec,
                packages=get_runner_requirements(config=self.config),
                verbose=self.verbose,
            )

            if worktree is not None and python_spec is not None:
                # pop all cleanups and re-push env YAML save
                ctx.pop_all()
                ctx.callback(self.save)

            name = name or f"env_{len(self.environments) + 1}"

            created = datetime.now().strftime(self.fmt)

            environment = BenchmarkEnvironment(
                name=name,
                worktree=worktree,
                python=python_spec,
                created=created,
                lastmod=created,
            )

            self.environments[name] = environment

            print(f"Successfully created benchmark environment for ref {commit_ish!r}.")

        return environment

    def delete(self, identifier: str, force: bool) -> BenchmarkEnvironment:
        with ExitStack() as ctx:
            ctx.callback(self.save)

            env_to_remove = self.get(identifier)
            env_name = env_to_remove.name

            print(
                f"Found matching benchmark environment {env_name!r}, "
                "starting removal."
            )

            venv_root = Path(env_to_remove.get_value("python.root"))
            worktree_root = Path(env_to_remove.get_value("worktree.root"))

            # Remove venv first if inside the worktree to avoid git problems
            if venv_root.exists() and venv_root.parent == worktree_root:
                self.builder.delete(venv_root, verbose=self.verbose)

            self.git_worktree.remove(str(worktree_root), force=force)

            env_to_remove = self.environments.pop(env_name)

            print(f"Successfully removed benchmark environment {env_name!r}.")

        return env_to_remove

    def get(self, value: Any) -> BenchmarkEnvironment:
        # check for known git info, otherwise use name
        info = disambiguate_info(value)
        attr = "worktree " + info if info else "name"

        if self.verbose:
            print(f"Matching benchmark environment with {attr} {value!r}.....", end="")
        try:
            if info is not None:
                env = next(
                    e
                    for e in self.environments.values()
                    if e.worktree == self.git_worktree.get_worktree_by_attr(info, value)
                )
            else:
                env = self.environments[value]

            if self.verbose:
                print("success.")

            return env
        except (StopIteration, KeyError):
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
        for env in self.environments.values():
            root: str = env.get_value("worktree.root")

            values = [env.get_value("name")]
            values.extend(env.worktree.get_ref_and_type())
            values.append(abbrev_home(root))
            values.append(env.get_value("python.version"))
            env_data.append(values)

        column_widths = calculate_column_widths(env_data)

        for i, d in enumerate(env_data):
            print(make_line(d, column_widths, padding=padding))
            if i == 0:
                print(make_separator(column_widths, padding=padding))

    def sync(self):
        with ExitStack() as ctx:
            ctx.callback(self.save)
            for i, worktree in enumerate(self.git_worktree.list()):
                venv_root = Path(worktree.root) / "venv"

                if venv_root.exists():
                    python_spec = self.builder.link(venv_root, verbose=self.verbose)
                else:
                    # TODO: Enable auto-grabbing from venv home
                    python_spec = self.builder.create(sys.executable, venv_root)

                created = datetime.now().strftime(self.fmt)

                name = "root" if is_main_worktree(worktree.root) else f"env_{i + 1}"

                env = BenchmarkEnvironment(
                    name=name,
                    worktree=worktree,
                    python=python_spec,
                    created=created,
                    lastmod=created,
                )

                self.environments[name] = env

    def switch(self, name: str, ref: str) -> BenchmarkEnvironment:
        ref_type = disambiguate_info(ref)

        with ExitStack() as ctx:
            ctx.callback(self.save)

            env = self.get(name)

            if self.verbose:
                print(
                    f"Switching checkout of environment {name!r} to {ref_type} {ref!r}."
                )

            worktree = self.git_worktree.switch(
                worktree=env.worktree, ref=ref, ref_type=ref_type
            )

            env.worktree = worktree

        return env
