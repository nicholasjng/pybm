import os
import sys
from typing import List, Dict, Text, Any, Callable

from pybm.command import CLICommand
from pybm.exceptions import ArgumentError
from pybm.git import git
from pybm.git_utils import is_git_repository
from pybm.status_codes import ERROR, SUCCESS
from pybm.venv import venv_builder

Options = Dict[Text, Any]
EnvHandlers = Dict[Text, Callable[[Options, bool], int]]


class EnvCommand(CLICommand):
    """
    Create and manage pybm benchmark environments.
    """
    # TODO: Better formatting through argparse formatter subclass
    usage = "pybm env create <commit-ish> <dest> [<options>]\n" \
            "   or: pybm env delete <identifier> [<options>]\n" \
            "   or: pybm env install <deps> [<options>]\n" \
            "   or: pybm env list\n" \
            "   or: pybm env update <env> <attr> <value>\n"

    def __init__(self, name: str):
        super(EnvCommand, self).__init__(name=name)

    def add_arguments(self, subcommand: str = None):
        if subcommand == "create":
            self.parser.add_argument("commit-ish",
                                     metavar="<commit-ish>",
                                     help="Commit, branch or tag to create a "
                                          "git worktree for.")
            self.parser.add_argument("dest",
                                     metavar="<dest>",
                                     nargs="?",
                                     default=None,
                                     help="Destination directory of "
                                          "the new worktree. Defaults to "
                                          "repository-name@"
                                          "{commit|branch|tag}.")
            self.parser.add_argument("-f", "--force",
                                     action="store_true",
                                     default=False,
                                     help="Force worktree creation. Useful for "
                                          "checking out a branch multiple "
                                          "times with different custom "
                                          "requirements.")
            self.parser.add_argument("-R", "--resolve-commits",
                                     action="store_true",
                                     default=False,
                                     help="Always resolve the given git ref to "
                                          "its associated commit. If the given "
                                          "ref is a branch name, this detaches "
                                          "the HEAD "
                                          "(see https://git-scm.com/docs/"
                                          "git-checkout#_detached_head).")
            self.parser.add_argument("-t",
                                     type=str,
                                     default=None,
                                     metavar="<tag>",
                                     help="Tag for the created "
                                          "environment (e.g. 'my-env'). "
                                          "Can be used to reference "
                                          "environments from the command "
                                          "line.")
            self.parser.add_argument("--no-checkout",
                                     action="store_true",
                                     default=False,
                                     help="Skip worktree checkout after "
                                          "creation. Useful for sparsely "
                                          "checking out branches.")
            self.parser.add_argument("-L", "--link-existing",
                                     type=str,
                                     default=None,
                                     metavar="<path-to-venv>",
                                     help="Link an existing Python virtual "
                                          "environment to the created pybm "
                                          "environment. Raises an error if "
                                          "the path not exist or is not "
                                          "recognized as a Python "
                                          "environment.")
            self.parser.add_argument("-C", "--create-venv",
                                     action="store_true",
                                     default=False,
                                     help="Create a Python virtual environment "
                                          "for the new pybm "
                                          "environment to enable "
                                          "benchmarking with custom "
                                          "requirements. This directory is "
                                          "either added to the worktree "
                                          "directly, or into $PYBM_VENV_HOME "
                                          "if the environment variable is set.")
            self.parser.add_argument("--python",
                                     type=str,
                                     default=sys.executable,
                                     help="Python interpreter to use in "
                                          "virtual environment construction.",
                                     metavar="<python>")
            self.parser.add_argument("--venv-options",
                                     type=str,
                                     default="",
                                     help="Comma- or space-separated list of "
                                          "command line options for virtual "
                                          "environment creation using venv. To "
                                          "get a comprehensive list of "
                                          "options, run `python -m venv -h`.",
                                     metavar="<venv-options>")
        elif subcommand == "delete":
            self.parser.add_argument("identifier",
                                     metavar="<identifier>",
                                     help="Information that uniquely "
                                          "identifies the environment. "
                                          "Can be checked out "
                                          "commit, branch name, directory, "
                                          "or custom user-defined tags.")
            self.parser.add_argument("-f", "--force",
                                     action="store_true",
                                     help="Force worktree destruction, "
                                          "removing untracked files and "
                                          "changes in the process.")
        elif subcommand == "install":
            self.parser.add_argument("-r",
                                     type=str,
                                     default=None,
                                     metavar="<requirements>",
                                     help="Requirements file for dependency "
                                          "installation in the newly created "
                                          "virtual environment.")
            self.parser.add_argument("--pip-options",
                                     type=str,
                                     default="",
                                     help="Comma- or space-separated list of "
                                          "command line options for dependency "
                                          "installation in the created virtual "
                                          "environment using pip. To get a "
                                          "comprehensive list of options, "
                                          "run `python -m pip install -h`.",
                                     metavar="<pip-options>")
        elif subcommand == "list":
            pass
        elif subcommand == "update":
            pass

    def create(self, options: Options, verbose: bool):
        if not is_git_repository(os.getcwd()):
            raise ArgumentError("No git repository present in this path.")

        commit_ish = options["commit-ish"]
        destination = options["dest"]
        force = options["force"]
        checkout = not options["no_checkout"]
        resolve_commits = options["resolve_commits"]
        create_venv = options["create_venv"]
        link_dir = options["link_existing"]
        python = options["python"]
        venv_options = options["venv_options"]

        wt = git.add_worktree(commit_ish=commit_ish,
                              destination=destination,
                              force=force,
                              checkout=checkout,
                              resolve_commits=resolve_commits)

        if verbose:
            print(f"Created worktree spec: {wt}")

        if create_venv:
            dest = wt["worktree"]
            env_spec = venv_builder.create_environment(
                python,
                destination=dest,
                option_string=venv_options)
            if verbose:
                print(f"Created virtual environment spec: {env_spec}")

        return SUCCESS

    def delete(self, options: Options, verbose: bool):
        if not is_git_repository(os.getcwd()):
            raise ArgumentError("No git repository present in this path.")

        identifier = options["identifier"]
        force = options["force"]

        wt = git.remove_worktree(identifier,
                                 force=force)
        if verbose:
            print(f"Deleted worktree: {wt}")

        return SUCCESS

    def install(self, options: Options, verbose: bool):
        pass

    def list(self, options: Options, verbose: bool):
        pass

    def update(self, options: Options, verbose: bool):
        pass

    def run(self, args: List[str]):
        subcommand_handlers: EnvHandlers = {
            "create": self.create,
            "delete": self.delete,
            "install": self.install,
            "list": self.list,
            "update": self.update,
        }
        if not args or args[0] not in subcommand_handlers:
            self.parser.print_help()
            return ERROR

        subcommand, *args = args

        self.add_arguments(subcommand=subcommand)

        options: Options = vars(self.parser.parse_args(args))

        verbose: bool = options.pop("v")
        if verbose:
            print(f"Parsed command line options: {options}")

        return subcommand_handlers[subcommand](options, verbose)
