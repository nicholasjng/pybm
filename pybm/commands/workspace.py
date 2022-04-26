import argparse
import sys

from typing import List, Callable, Mapping

from pybm.exceptions import ProviderError, PybmError
from pybm.providers import BaseProvider, PythonVenvProvider
from pybm.command import CLICommand
from pybm.config import PybmConfig
from pybm.git import GitWorktreeWrapper
from pybm.logging import get_logger
from pybm.mixins.filemanager import WorkspaceManagerContextMixin
from pybm.specs import EmptyPythonSpec
from pybm.status_codes import ERROR, SUCCESS
from pybm.util.formatting import (
    abbrev_home,
    calculate_column_widths,
    make_line,
    make_separator,
)
from pybm.workspace import Workspace

logger = get_logger(__name__)

EnvSubcommand = Callable[[argparse.Namespace], int]


class WorkspaceCommand(WorkspaceManagerContextMixin, CLICommand):
    """
    Inspect, list, and manage pybm benchmark workspaces.
    """

    usage = (
        "pybm workspace install <name> <packages> [<options>]\n"
        "   or: pybm workspace link <name> <path>\n"
        "   or: pybm workspace list\n"
        "   or: pybm workspace sync [<options>]\n"
        "   or: pybm workspace uninstall <name> <packages> [<options>]\n"
    )

    def __init__(self):
        config = PybmConfig.load()
        super().__init__(name="workspace")

        # git worktree wrapper and provider class
        self.git_worktree = GitWorktreeWrapper()

        # relevant config attributes
        self.datefmt = config.get_value("core.datefmt")

    def add_arguments(self, subcommand: str = None):
        assert subcommand is not None, "no valid subcommand specified"

        if subcommand == "install":
            self.parser.add_argument(
                "name",
                metavar="<name>",
                help="Information that uniquely identifies the workspace. Can be "
                "name, checked out (partial) commit/branch/tag, or worktree directory.",
            )
            self.parser.add_argument(
                "packages",
                nargs="*",
                default=list(),
                metavar="<packages>",
                help="Packages to install into the newly created virtual environment.",
            )
            self.parser.add_argument(
                "--provider",
                type=str,
                default=None,
                choices=("stdlib",),
                metavar="<provider>",
                help="Provider component to use for virtual environment creation.",
            )
            self.parser.add_argument(
                "--install-option",
                default=list(),
                action="append",
                metavar="<options>",
                dest="options",
                help="Additional installation options passed to the provider "
                "component. Can be repeated with multiple options.",
            )
        elif subcommand == "link":
            self.parser.add_argument(
                "name",
                metavar="<name>",
                help="Information that uniquely identifies the workspace. Can be "
                "name, checked out (partial) commit/branch/tag, or worktree directory.",
            )
            self.parser.add_argument(
                "path",
                metavar="<path>",
                help="Path to the virtual environment that should be linked to the "
                "chosen workspace.",
            )
        elif subcommand == "sync":
            self.parser.add_argument(
                "--force-create-env",
                action="store_true",
                default=False,
                help="Create a virtual environment in-tree if linking fails.",
            )
        elif subcommand == "uninstall":
            self.parser.add_argument(
                "name",
                metavar="<name>",
                help="Information that uniquely identifies the workspace. Can be "
                "name, checked out (partial) commit/branch/tag, or worktree directory.",
            )
            self.parser.add_argument(
                "packages",
                nargs="*",
                default=list(),
                metavar="<packages>",
                help="Packages to uninstall from the existing virtual environment.",
            )
            self.parser.add_argument(
                "--uninstall-option",
                default=list(),
                action="append",
                metavar="<options>",
                dest="options",
                help="Additional uninstallation options passed to the provider "
                "component. Can be repeated with multiple options.",
            )

    def install(self, options: argparse.Namespace):
        option_dict = vars(options)

        verbose: bool = option_dict.pop("verbose")

        # env name / git worktree info
        info: str = option_dict.pop("identifier")

        packages: List[str] = option_dict.pop("packages")
        install_options: List[str] = option_dict.pop("options")

        provider: BaseProvider = PythonVenvProvider()

        with self.main_context(verbose=verbose, readonly=False):
            workspace = self.get(info)

            provider.add(
                workspace=workspace,
                packages=packages,
                options=install_options,
                verbose=verbose,
            )
            workspace.update_packages()

        return SUCCESS

    def link(self, options: argparse.Namespace):
        option_dict = vars(options)

        verbose: bool = option_dict.pop("verbose")

        # env name / git worktree info
        info: str = option_dict.pop("identifier")

        path: str = option_dict.pop("path")

        provider: BaseProvider = PythonVenvProvider()

        with self.main_context(verbose=verbose, readonly=False):
            workspace = self.get(info)

            spec = provider.link(path=path, verbose=verbose)

            # TODO: Provide an official API here, this approach sucks
            workspace.executable = spec.executable
            workspace.version = spec.version
            workspace.update_packages()

        return SUCCESS

    def list(self, options: argparse.Namespace):
        option_dict = vars(options)

        verbose: bool = option_dict.pop("verbose")
        padding: int = option_dict.pop("padding", 1)

        column_names = [
            "Name",
            "Git Reference",
            "Reference type",
            "Worktree directory",
            "Python version",
        ]

        with self.main_context(verbose=verbose, readonly=True):
            env_data = [column_names]
            for workspace in self.workspaces.values():
                root = workspace.root

                values = [workspace.name]
                values.extend(workspace.get_ref_and_type())
                values.append(abbrev_home(root))
                values.append(workspace.version)
                env_data.append(values)

            column_widths = calculate_column_widths(env_data)

            for i, d in enumerate(env_data):
                print(make_line(d, column_widths, padding=padding))
                if i == 0:
                    print(make_separator(column_widths, padding=padding))

        return SUCCESS

    def sync(self, options: argparse.Namespace):
        option_dict = vars(options)

        verbose: bool = option_dict.pop("verbose")
        force_creation: bool = option_dict.pop("force_create_env")

        provider: BaseProvider = PythonVenvProvider()

        with self.main_context(verbose=verbose, readonly=False):
            for i, worktree in enumerate(self.git_worktree.list()):
                try:
                    self.get(worktree.root, verbose=verbose)
                    # TODO: Update worktree information
                except PybmError:
                    try:
                        python_spec = provider.link(worktree.root, verbose=verbose)
                    except ProviderError:
                        if force_creation:
                            python_spec = provider.create(
                                executable=sys.executable,
                                destination=worktree.root,
                            )
                        else:
                            python_spec = EmptyPythonSpec

                    name = "main" if i == 0 else f"workspace_{i + 1}"

                    self.workspaces[name] = Workspace(
                        name=name,
                        worktree=worktree,
                        spec=python_spec,
                    )

    def uninstall(self, options: argparse.Namespace):
        option_dict = vars(options)

        verbose: bool = option_dict.pop("verbose")

        info: str = option_dict.pop("identifier")

        packages: List[str] = option_dict.pop("packages", [])
        uninstall_options: List[str] = option_dict.pop("options", [])

        provider: BaseProvider = PythonVenvProvider()

        with self.main_context(verbose=verbose, readonly=False):
            workspace = self.get(info)

            provider.remove(
                workspace=workspace,
                packages=packages,
                options=uninstall_options,
                verbose=verbose,
            )
            workspace.update_packages()

        return SUCCESS

    def run(self, args: List[str]):
        logger.debug(f"Running command `{self.format_call(args)}`.")

        subcommand_handlers: Mapping[str, EnvSubcommand] = {
            "install": self.install,
            "link": self.link,
            "list": self.list,
            "sync": self.sync,
            "uninstall": self.uninstall,
        }

        if not args or all(arg.startswith("-") for arg in args):
            subcommand = "list"
        else:
            subcommand, *args = args

        if subcommand not in subcommand_handlers:
            self.parser.print_help()
            return ERROR

        self.add_arguments(subcommand=subcommand)

        options = self.parser.parse_args(args)

        return subcommand_handlers[subcommand](options)
