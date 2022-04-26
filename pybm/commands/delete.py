from pathlib import Path
from typing import List

from pybm.exceptions import PybmError
from pybm.providers import BaseProvider, PythonVenvProvider
from pybm.command import CLICommand
from pybm.git import GitWorktreeWrapper
from pybm.logging import get_logger
from pybm.mixins.filemanager import WorkspaceManagerContextMixin
from pybm.providers.util import get_venv_root
from pybm.specs import PythonSpec
from pybm.status_codes import ERROR, SUCCESS

logger = get_logger(__name__)


class DeleteCommand(WorkspaceManagerContextMixin, CLICommand):
    """
    Delete a pybm benchmark environment.
    """

    usage = "pybm delete <identifier> [<options>]\n"

    def __init__(self):
        super().__init__(name="delete")

        # git worktree wrapper and builder class
        self.git_worktree = GitWorktreeWrapper()

    def add_arguments(self):
        self.parser.add_argument(
            "identifier",
            metavar="<id>",
            help="Information that uniquely identifies the workspace. Can be name, "
            "checked out commit/branch/tag, or worktree directory.",
        )
        self.parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Force worktree removal, including untracked files.",
        )

    def run(self, args: List[str]):
        logger.debug(f"Running command `{self.format_call(args)}`.")

        if not args:
            self.parser.print_help()
            return ERROR

        self.add_arguments()

        options = self.parser.parse_args(args)

        option_dict = vars(options)

        # verbosity
        verbose: bool = option_dict.pop("verbose")

        # env name / git worktree info
        identifier: str = option_dict.pop("identifier")
        force: bool = option_dict.pop("force")

        provider: BaseProvider = PythonVenvProvider()

        with self.main_context(verbose=verbose, readonly=False):
            workspace = self.get(identifier, verbose=verbose)
            name = workspace.name

            if name == "main":
                raise PybmError("The 'main' workspace cannot be removed.")

            print(f"Removing matching benchmark workspace {name!r}.")

            venv_root = get_venv_root(workspace.executable)
            workspace_root = Path(workspace.root)

            spec = PythonSpec(
                executable=workspace.executable, version=workspace.version
            )

            # Remove venv first if inside the worktree to avoid git problems
            if venv_root.exists() and venv_root.parent == workspace_root:
                provider.delete(spec, verbose=verbose)

            self.git_worktree.remove(workspace.root, force=force)
            self.workspaces.pop(name)

            print(f"Successfully removed benchmark workspace {name!r}.")

        return SUCCESS
