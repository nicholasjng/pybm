import sys
from typing import List

from pybm.command import CLICommand
from pybm.exceptions import GitError
from pybm.git import git
from pybm.git_utils import is_git_repository
from pybm.status_codes import ERROR, SUCCESS


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
                                 help="Commit, branch or tag to create a "
                                      "git worktree for.")
        self.parser.add_argument("dest",
                                 metavar="<dest>",
                                 nargs="?",
                                 default=None,
                                 help="Destination directory to create for "
                                      "the new worktree. Defaults to "
                                      "repository-name@{commit|branch|tag}.")
        self.parser.add_argument("--python",
                                 type=str,
                                 default=sys.executable,
                                 help="Python interpreter to use in "
                                      "virtual environment construction.",
                                 metavar="<python>")
        self.parser.add_argument("-f", "--force",
                                 action="store_true",
                                 default=False,
                                 help="Force worktree creation. Useful for "
                                      "checking out a branch multiple times "
                                      "with different custom requirements.")
        self.parser.add_argument("--no-checkout",
                                 action="store_true",
                                 default=False,
                                 help="Skip worktree checkout after creation. "
                                      "This can be used to sparsely "
                                      "check out branches.")
        self.parser.add_argument("-R", "--resolve-commits",
                                 action="store_true",
                                 default=False,
                                 help="Always resolve the given git ref to "
                                      "its associated commit. If the given "
                                      "ref is a branch name, this detaches "
                                      "the HEAD (see https://git-scm.com/docs/"
                                      "git-checkout#_detached_head).")

    def run(self, args: List[str]):
        self.add_arguments()

        if not args:
            self.parser.print_help()
            return ERROR

        namespace = self.parser.parse_args(args)
        var_dict = vars(namespace)

        verbose = var_dict.pop("v")
        if verbose:
            print(f"Parsed command line options: {var_dict}")

        if not is_git_repository():
            raise GitError("No git repository present in this path")

        git.add_worktree(var_dict["commit-ish"],
                         name=var_dict["dest"],
                         force=var_dict["force"],
                         checkout=not var_dict["no_checkout"],
                         resolve_commits=var_dict["resolve_commits"]
                         )

        return SUCCESS
