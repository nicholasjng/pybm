import sys

from pybm.command import CLICommand
from pybm.exceptions import GitError
from pybm.git import GitWorktreeWrapper
from pybm.git_utils import is_git_repository
from pybm.status_codes import SUCCESS, ERROR


class CreateCommand(CLICommand):
    """
    Create a pybm benchmark environment.
    """
    usage = "pybm create <commit-ish> <dest> [<options>]"

    def __init__(self, name: str):
        super(CreateCommand, self).__init__(name=name)

    def add_arguments(self):
        self.parser.add_argument("commit-ish",
                                 metavar="<commit-ish>",
                                 nargs=1,
                                 help="Commit, branch or tag to create a "
                                      "git worktree for.")
        self.parser.add_argument("dest",
                                 metavar="<dest>",
                                 default=None,
                                 help="Destination directory for the newly "
                                      "created worktree. Defaults to "
                                      "repository-name@{commit|branch|tag}.")
        self.parser.add_argument("--python",
                                 type=str,
                                 default=sys.executable,
                                 help="Python interpreter to use in "
                                      "virtual environment construction.",
                                 metavar="<python>")
        self.parser.add_argument("-f", "--force",
                                 action="store_true",
                                 help="Force worktree creation. Useful for "
                                      "checking out a branch multiple times "
                                      "with different custom requirements.")
        self.parser.add_argument("--no-checkout",
                                 action="store_true",
                                 help="Skip worktree checkout after creation. "
                                      "This can be used to sparsely "
                                      "check out branches where only a small "
                                      "subset of code needs to be run.")

    def run(self, *args, **kwargs) -> int:
        self.add_arguments()

        namespace = self.parser.parse_args(*args)
        var_dict = vars(namespace)

        if not is_git_repository():
            raise GitError("No git repository present in this path")

        git = GitWorktreeWrapper()

        git.add_worktree(var_dict["commit-ish"],
                         var_dict["dest"],
                         force=var_dict["f"]
                         )

        return SUCCESS
