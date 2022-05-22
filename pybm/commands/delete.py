from typing import List

from pybm.command import CLICommand
from pybm.exceptions import PybmError
from pybm.git import GitWorktreeWrapper
from pybm.logging import get_logger
from pybm.mixins.filemanager import WorkspaceManagerContextMixin
from pybm.statuscodes import ERROR, SUCCESS

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

        # verbose mode
        verbose: bool = options.verbose

        with self.main_context(verbose=verbose, readonly=False):
            workspace = self.get(options.identifier, verbose=verbose)
            venv, name = workspace.venv, workspace.name

            if name == "main":
                raise PybmError("The 'main' workspace cannot be removed.")

            print(f"Removing benchmark workspace {name!r}.")

            # Remove venv first if inside the worktree to avoid git problems
            if workspace.venv_in_tree():
                venv.delete()

            self.git_worktree.remove(workspace.root, force=options.force)
            self.workspaces.pop(name)

            print(f"Successfully removed benchmark workspace {name!r}.")

        return SUCCESS
