from contextlib import ExitStack, contextmanager
from functools import partial
from pathlib import Path
from typing import ContextManager, Dict, TypeVar

import yaml

from pybm.config import config
from pybm.exceptions import PybmError
from pybm.util.common import dvmap
from pybm.util.git import disambiguate_info
from pybm.workspace import Workspace

_T = TypeVar("_T", covariant=True)


class WorkspaceManagerContextMixin:
    """
    Thin shim around a contextlib.ExitStack object for loading and manipulating
    TOML files containing pybm benchmark workspace information.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._in_main_context = False
        self._main_context = ExitStack()

        # relevant config attributes
        self.workspace_file = Path(config.get_value("core.workspacefile"))

        self.workspaces: Dict[str, Workspace] = {}

    @contextmanager
    def main_context(
        self, verbose: bool = False, missing_ok: bool = False, readonly: bool = True
    ):
        assert not self._in_main_context

        self._in_main_context = True
        try:
            with self._main_context:
                self.load(verbose=verbose, missing_ok=missing_ok)
                # register save callback if envs are mutated (write to disk)
                if not readonly:
                    self._main_context.callback(partial(self.save, verbose=verbose))
                yield self._main_context
        finally:
            self._in_main_context = False

    def enter_context(self, context_provider: ContextManager[_T]) -> _T:
        assert self._in_main_context

        return self._main_context.enter_context(context_provider)

    def get(self, value: str, verbose: bool = False) -> Workspace:
        if not self._in_main_context:
            raise PybmError(
                "Not inside a file manager context. Workspace snapshots have not yet "
                "been loaded, please move usage of the get() method inside the main "
                "file manager context."
            )
        # check for known git info, otherwise use name
        info = disambiguate_info(value)
        attr = "worktree " + info if info else "name"

        if verbose:
            print(f"Matching workspace with {attr} {value!r}.....", end="")
        try:
            if info is not None:
                workspace = next(
                    e for e in self.workspaces.values() if getattr(e, info) == value
                )
            else:
                # value is workspace name
                workspace = self.workspaces[value]

            if verbose:
                print("success.")

            return workspace
        except (StopIteration, KeyError):
            if verbose:
                print("failed.")

            raise PybmError(f"Workspace with {attr} {value!r} does not exist.")

    def load(self, verbose: bool = False, missing_ok: bool = False):
        if not self.workspace_file.exists():
            if not missing_ok:
                raise PybmError(
                    "No workspace configuration file found. To create a "
                    "configuration file and a default workspace, run `pybm "
                    "init` from the root of your git repository."
                )
            else:
                return {}
        else:
            if verbose:
                print(
                    f"Loading workspaces from file {self.workspace_file}.....",
                    end="",
                )
            try:
                with open(self.workspace_file, "r") as cfg:
                    workspaces = yaml.load(cfg, Loader=yaml.FullLoader)

                if verbose:
                    print("done.")
            except OSError:
                if verbose:
                    print("failed.")
                raise

            for name, obj in workspaces.items():
                self.workspaces[name] = Workspace.deserialize(obj)

    def save(self, verbose: bool = False):
        workspaces = dvmap(lambda x: x.serialize(), self.workspaces)

        if verbose:
            print(
                f"Saving workspace snapshots to file {self.workspace_file}.....",
                end="",
            )
        try:
            with open(self.workspace_file, "w") as cfg:
                yaml.dump(workspaces, cfg)

            if verbose:
                print("done.")
        except OSError:
            if verbose:
                print("failed.")
            raise
