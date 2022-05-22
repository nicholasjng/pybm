import sys
from pathlib import Path
from typing import List, Optional

from pybm.command import CLICommand
from pybm.config import config as local_config
from pybm.config import global_config
from pybm.exceptions import PybmError
from pybm.git import GitWorktreeWrapper
from pybm.mixins.filemanager import WorkspaceManagerContextMixin
from pybm.statuscodes import SUCCESS
from pybm.util.git import is_main_worktree
from pybm.util.path import get_filenames
from pybm.venv import PythonVenv
from pybm.workspace import _MAIN_NAME, Workspace


def init_default_workspace(
    link_dir: Optional[str] = None,
    executable: str = sys.executable,
    install: bool = True,
    with_dependencies: bool = True,
    create_options: Optional[List[str]] = None,
    install_options: Optional[List[str]] = None,
    extra_packages: Optional[List[str]] = None,
    verbose: bool = False,
) -> Workspace:
    worktree = GitWorktreeWrapper().get_main_worktree()

    # either create venv in worktree or link from outside
    if link_dir is None:
        in_tree = True
        directory = worktree.root
    else:
        in_tree = False
        directory = link_dir

    venv = PythonVenv(
        directory=directory,
        executable=executable,
    ).create(options=create_options, in_tree=in_tree)

    if install:
        venv.install(
            directory=worktree.root,
            with_dependencies=with_dependencies,
            extra_packages=extra_packages,
            options=install_options,
            verbose=verbose,
        )

    return Workspace(name=_MAIN_NAME, worktree=worktree, venv=venv)


class InitCommand(WorkspaceManagerContextMixin, CLICommand):
    """
    Initialize pybm by setting config values and creating a main benchmark workspace.
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
            "--link-existing",
            type=str,
            default=None,
            dest="link_dir",
            metavar="<path>",
            help="Link an existing Python virtual environment directory to the main "
            "workspace.",
        )
        self.parser.add_argument(
            "--no-install",
            action="store_true",
            default=False,
            help="Skip project installation at the chosen git reference.",
        )
        self.parser.add_argument(
            "--no-deps",
            action="store_true",
            default=False,
            help="Do not install project dependencies.",
        )
        self.parser.add_argument(
            "--python",
            type=str,
            default=sys.executable,
            dest="executable",
            help="Python interpreter to use for the main workspace's virtual "
            "environment.",
            metavar="<python>",
        )
        self.parser.add_argument(
            "--create-option",
            default=list(),
            action="append",
            metavar="<option>",
            dest="create_options",
            help="Additional creation options passed to Python's venv. "
            "Can be used multiple times to supply multiple options.",
        )
        self.parser.add_argument(
            "--install-option",
            default=list(),
            action="append",
            metavar="<option>",
            dest="install_options",
            help="Additional installation options passed to `pip install`. "
            "Can be used multiple times to supply multiple options.",
        )
        self.parser.add_argument(
            "--extra-packages",
            default=list(),
            action="append",
            metavar="<pkg-name>",
            help="Additional packages to install into the main benchmark workspace.",
        )

    def run(self, args: List[str]) -> int:
        self.add_arguments()

        options = self.parser.parse_args(args)

        verbose: bool = options.verbose
        skip_global: bool = options.skip_global
        overrides: List[str] = options.overrides

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
                (config_dir / p).unlink()

        local_config.save()

        with self.main_context(verbose=verbose, missing_ok=True, readonly=False):
            self.workspaces["main"] = init_default_workspace(
                link_dir=options.link_dir,
                executable=options.executable,
                with_dependencies=not options.no_deps,
                create_options=options.create_options,
                install_options=options.install_options,
                extra_packages=options.extra_packages,
                verbose=verbose,
            )

        return SUCCESS
