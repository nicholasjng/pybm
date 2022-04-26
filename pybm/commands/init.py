import sys
from pathlib import Path
from typing import List, Optional

from pybm.command import CLICommand
from pybm.config import (
    config as local_config,
    global_config,
    get_component,
    LOCAL_CONFIG,
)
from pybm.exceptions import PybmError
from pybm.git import GitWorktreeWrapper
from pybm.mixins.filemanager import WorkspaceManagerContextMixin
from pybm.providers import BaseProvider
from pybm.status_codes import SUCCESS
from pybm.util.git import is_main_worktree
from pybm.util.path import get_filenames
from pybm.workspace import Workspace, _MAIN_NAME


def init_default_workspace(
    provider: Optional[BaseProvider] = None, link_only: bool = False
) -> Workspace:
    worktree = GitWorktreeWrapper().get_main_worktree()

    if not provider:
        provider = get_component("provider")

    # keep mypy happy
    assert provider is not None

    if link_only:
        spec = provider.link(path=worktree.root)
    else:
        spec = provider.create(executable=sys.executable, destination=worktree.root)

    return Workspace(name=_MAIN_NAME, worktree=worktree, spec=spec)


class InitCommand(WorkspaceManagerContextMixin, CLICommand):
    """
    Initialize pybm in a git repository by adding a configuration file
    and an environment list into a directory.
    """

    usage = "pybm init [<options>]\n"

    def __init__(self):
        super(InitCommand, self).__init__(name="init")

    def add_arguments(self):
        self.parser.add_argument(
            "--rm",
            action="store_true",
            default=False,
            dest="remove_existing",
            help="Overwrite any existing configuration.",
        )
        self.parser.add_argument(
            "-o",
            "--override",
            action="append",
            default=list(),
            dest="overrides",
            help="Override a specific configuration setting with a custom value "
            "for the new pybm configuration file. Supplied arguments need to have the "
            "form 'key=value'. For a comprehensive list of configuration options, "
            "run `pybm config list`.",
        )
        self.parser.add_argument(
            "--skip-global",
            action="store_true",
            default=False,
            help="Skip applying system-wide defaults set in the global config file to "
            "the newly created pybm configuration.",
        )
        self.parser.add_argument(
            "--provider",
            type=str,
            default=None,
            choices=("stdlib",),
            metavar="<provider>",
            help="Python provider to use for virtual environment setup.",
        )

    def run(self, args: List[str]) -> int:
        self.add_arguments()

        options = self.parser.parse_args(args)

        verbose: bool = options.verbose
        skip_global: bool = options.skip_global
        overrides: List[str] = options.overrides
        provider: BaseProvider = options.provider

        if verbose:
            print(f"Parsed command line options: {options}")

        if not is_main_worktree(Path.cwd()):
            raise PybmError(
                "Cannot initialize pybm: Current directory is not a git repository."
            )

        if global_config is not None and not skip_global:
            for k, v in global_config.items():
                if v is not None:
                    if verbose:
                        print(f"Setting global config value {k} = {v}.")
                    local_config.set_value(k, v)

        for override in overrides:
            try:
                attr, value = override.split("=", maxsplit=1)
            except ValueError:
                raise PybmError(
                    "Config overrides need to be specified in the form 'attr=value'."
                )

            if verbose:
                print(f"Overriding config option {attr!r} with value {value!r}.")

            local_config.set_value(attr, value)

        # ensure the config directory exists
        config_dir = Path(".pybm")
        config_dir.mkdir(parents=False, exist_ok=True)

        if options.remove_existing:
            for p in get_filenames(config_dir, file_ext=".yaml"):
                Path(p).unlink()

        # TODO: Make this dynamic from a config option / CLI option
        error_on_exist = False
        if Path(LOCAL_CONFIG) and error_on_exist:
            raise PybmError(
                "Configuration file already exists. If you want to overwrite the "
                "existing configuration, run `pybm init --rm`."
            )

        local_config.save()

        with self.main_context(verbose=verbose, missing_ok=True, readonly=False):
            self.workspaces["main"] = init_default_workspace(
                provider=provider, link_only=True
            )

        return SUCCESS
