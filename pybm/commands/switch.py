# from datetime import datetime
from typing import List

from pybm.config import config
from pybm.command import CLICommand
from pybm.git import GitWorktreeWrapper
from pybm.logging import get_logger
from pybm.mixins.filemanager import WorkspaceManagerContextMixin
from pybm.status_codes import ERROR, SUCCESS
from pybm.util.git import disambiguate_info

logger = get_logger(__name__)


class SwitchCommand(WorkspaceManagerContextMixin, CLICommand):
    """Switch checkout of a pybm benchmark environment."""

    usage = "pybm switch <name> <ref> [<options>]\n"

    def __init__(self):
        super().__init__(name="switch")

        self.git_worktree = GitWorktreeWrapper()

        # datefmt attribute for last-modified timestamp
        self.datefmt = config.get_value("core.datefmt")

    def add_arguments(self):
        self.parser.add_argument(
            "name",
            metavar="<name>",
            help="Name of the benchmark workspace to switch checkout for.",
        )
        self.parser.add_argument(
            "ref",
            metavar="<ref>",
            help="New git reference to check out in the given workspace. Can be a "
            "branch name, tag, or (partial) commit SHA.",
        )

    def run(self, args: List[str]):
        logger.debug(f"Running command `{self.format_call(args)}`.")

        if not args:
            self.parser.print_help()
            return ERROR

        self.add_arguments()

        options = self.parser.parse_args(args)

        name: str = options.name
        new_ref: str = options.ref
        verbose: bool = options.verbose

        with self.main_context(verbose=verbose, readonly=False):
            ref_type = disambiguate_info(new_ref)

            workspace = self.get(name)
            old_ref = workspace.get_ref_and_type()[0]
            old_root = workspace.root

            if verbose:
                print(
                    f"Switching checkout of workspace {name!r} to {ref_type} "
                    f"{new_ref!r}."
                )

            workspace.switch(ref=new_ref, ref_type=ref_type)

            if old_ref in old_root:
                worktree = self.git_worktree.get_worktree_by_attr("root", old_root)
                new_root = old_root.replace(old_ref, new_ref)

                # `git worktree move` renames worktree root
                self.git_worktree.move(worktree=worktree, new_path=new_root)

                # set it in the Python object as well
                setattr(workspace, "root", new_root)

        print(f"Successfully checked out {ref_type} {new_ref!r} in workspace {name!r}.")

        return SUCCESS
