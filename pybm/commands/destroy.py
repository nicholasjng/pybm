import sys

from pybm.command import CLICommand
from pybm.exceptions import GitError
from pybm.git import GitWorktreeWrapper
from pybm.git_utils import is_git_repository
from pybm.status_codes import SUCCESS, ERROR


class DestroyCommand(CLICommand):
    """
    Remove a pybm benchmark environment.
    """
    usage = "pybm destroy <commit-ish> [<options>]"

    def __init__(self, name: str):
        super(DestroyCommand, self).__init__(name=name)

    def add_arguments(self):
        self.parser.add_argument("commit-ish",
                                 metavar="<commit-ish>",
                                 help="Commit, branch or tag to create a "
                                      "git worktree for.")
        self.parser.add_argument("-f", "--force",
                                 action="store_true",
                                 help="Force worktree creation. Useful for "
                                      "checking out a branch multiple times "
                                      "with different custom requirements.")
        self.parser.add_argument("-v",
                                 action="count",
                                 default=0,
                                 help="Enable verbose mode. This causes pybm "
                                      "to log information useful for "
                                      "debugging.")

    def run(self, *args, **kwargs) -> int:
        self.add_arguments()

        namespace = self.parser.parse_args(*args)
        var_dict = vars(namespace)

        verbose = var_dict.pop("v")
        if verbose:
            print(var_dict)

        if not is_git_repository():
            raise GitError("No git repository present in this path.")

        git = GitWorktreeWrapper()

        git.remove_worktree(var_dict["commit-ish"],
                            force=var_dict["force"],
                            )

        return SUCCESS
