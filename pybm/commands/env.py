import sys
from typing import List, Dict, Text, Any, Callable

from pybm.command import CLICommand
from pybm.env_store import Environment, EnvDB
from pybm.git import git
from pybm.status_codes import ERROR, SUCCESS
from pybm.venv import venv_builder

Options = Dict[Text, Any]
EnvHandlers = Dict[Text, Callable[[Options, bool], int]]
WORKSPACE = "workspace"
PYTHON_ENV = "python_environment"


class EnvCommand(CLICommand):
    """
    Create and manage pybm benchmark environments.
    """
    # TODO: Better formatting through argparse formatter subclass
    usage = "pybm env create <commit-ish> <dest> [<options>]\n" \
            "   or: pybm env delete <identifier> [<options>]\n" \
            "   or: pybm env install <packages> [<options>]\n" \
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
                                     help="Force worktree creation. Useful "
                                          "for checking out a branch "
                                          "multiple times with different "
                                          "custom requirements.")
            self.parser.add_argument("-R", "--resolve-commits",
                                     action="store_true",
                                     default=False,
                                     help="Always resolve the given git "
                                          "ref to its associated commit. "
                                          "If the given ref is a branch "
                                          "name, this detaches the HEAD "
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
                                     help="Create a Python virtual "
                                          "environment for the new pybm "
                                          "environment to enable "
                                          "benchmarking with custom "
                                          "requirements. This directory is "
                                          "either added to the worktree "
                                          "directly, or into $PYBM_VENV_HOME "
                                          "if the environment variable is "
                                          "set.")
            self.parser.add_argument("--python",
                                     type=str,
                                     default=sys.executable,
                                     help="Python interpreter to use in "
                                          "virtual environment construction.",
                                     metavar="<python>")
            self.parser.add_argument("--venv-options",
                                     type=str,
                                     default=None,
                                     help="Comma- or space-separated list of "
                                          "command line options for virtual "
                                          "environment creation using venv. "
                                          "To get a comprehensive list of "
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
            self.parser.add_argument("packages",
                                     nargs="*",
                                     default=None,
                                     metavar="<packages>",
                                     help="Package dependencies to install "
                                          "into the new virtual environment "
                                          "using pip. All packages listed "
                                          "must be either pinned (in the "
                                          "format pkg==<semver-tag>) or "
                                          "unpinned (package name only).")
            self.parser.add_argument("-r",
                                     type=str,
                                     default=None,
                                     metavar="<requirements>",
                                     help="Requirements file for dependency "
                                          "installation in the newly created "
                                          "virtual environment.")
            self.parser.add_argument("--pip-options",
                                     type=str,
                                     default=None,
                                     help="Comma- or space-separated list of "
                                          "command line options for "
                                          "dependency installation in the "
                                          "created virtual environment "
                                          "using `pip install`. To get a "
                                          "comprehensive list of options, "
                                          "run `python -m pip install -h`.",
                                     metavar="<pip-options>")
        elif subcommand == "list":
            pass
        elif subcommand == "update":
            pass

    def create(self, options: Options, verbose: bool):
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
            print(f"Created worktree with spec: {wt}")

        env_spec = {}

        if create_venv:
            dest = wt["worktree"]
            env_spec = venv_builder.create(python, destination=dest,
                                           option_string=venv_options)
            if verbose:
                print(f"Created virtual environment with spec: {env_spec}")

        if link_dir is not None:
            env_spec = venv_builder.link_existing(link_dir)

        environment: Environment = {
            WORKSPACE: wt,
            PYTHON_ENV: env_spec,
        }

        if verbose:
            print(f"Created pybm environment: {environment}")

        EnvDB.add(environment=environment)

        return SUCCESS

    def delete(self, options: Options, verbose: bool):
        identifier = options["identifier"]
        force = options["force"]

        wt = git.remove_worktree(identifier,
                                 force=force)
        if verbose:
            print(f"Deleted worktree: {wt}")

        return SUCCESS

    def install(self, options: Options, verbose: bool):
        packages = options["packages"]
        requirements_file = options["requirements_file"]
        pip_options = options["pip_options"]

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
