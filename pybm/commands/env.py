import argparse
import sys
from typing import List

from pybm.builders.base import PythonEnvBuilder
from pybm.command import CLICommand
from pybm.config import PybmConfig, get_builder_class
from pybm.env_store import EnvironmentStore
from pybm.exceptions import PybmError
from pybm.logging import get_logger
from pybm.status_codes import ERROR, SUCCESS

logger = get_logger(__name__)


class EnvCommand(CLICommand):
    """
    Create and manage pybm benchmark environments.
    """
    # TODO: Better formatting through argparse formatter subclass
    usage = "pybm env create <commit-ish> <name> <dest> [<options>]\n" \
            "   or: pybm env delete <identifier> [<options>]\n" \
            "   or: pybm env install <packages> [<options>]\n" \
            "   or: pybm env uninstall <packages> [<options>]\n" \
            "   or: pybm env list\n" \
            "   or: pybm env update <env> <attr> <value>\n"

    def __init__(self):
        super(EnvCommand, self).__init__(name="env")
        config = PybmConfig.load(".pybm/config.yaml")
        self.config = config

    def add_arguments(self, subcommand: str = None):
        if subcommand == "create":
            self.parser.add_argument("commit_ish",
                                     metavar="<commit-ish>",
                                     help="Commit, branch or tag to create a "
                                          "git worktree for.")
            self.parser.add_argument("name",
                                     metavar="<name>",
                                     nargs="?",
                                     default=None,
                                     help="Unique name for the created "
                                          "environment. Can be used to "
                                          "reference environments from "
                                          "the command line.")
            self.parser.add_argument("destination",
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
            self.parser.add_argument("--no-checkout",
                                     action="store_true",
                                     default=False,
                                     help="Skip worktree checkout after "
                                          "creation. Useful for sparsely "
                                          "checking out branches.")
            self.parser.add_argument("-L", "--link-existing",
                                     type=str,
                                     default=None,
                                     dest="link_dir",
                                     metavar="<path-to-venv>",
                                     help="Link an existing Python virtual "
                                          "environment to the created pybm "
                                          "environment. Raises an error if "
                                          "the path does not exist or is not "
                                          "recognized as a valid Python "
                                          "virtual environment.")
            self.parser.add_argument("--python",
                                     type=str,
                                     default=sys.executable,
                                     dest="python_executable",
                                     help="Python interpreter to use in "
                                          "virtual environment construction.",
                                     metavar="<python>")
            self.parser.add_argument("--venv-options",
                                     nargs="*",
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
                                          "Can be name, checked out "
                                          "commit/branch/tag name or "
                                          "git worktree base directory.")
            self.parser.add_argument("-f", "--force",
                                     action="store_true",
                                     help="Force worktree removal, "
                                          "removing untracked files and "
                                          "changes in the process.")
        elif subcommand == "install":
            self.parser.add_argument("identifier",
                                     metavar="<identifier>",
                                     help="Information that uniquely "
                                          "identifies the environment. "
                                          "Can be name, checked out "
                                          "commit, branch name, directory, "
                                          "or custom user-defined tags.")
            self.parser.add_argument("packages",
                                     nargs="*",
                                     default=None,
                                     metavar="<packages>",
                                     help="Package dependencies to install "
                                          "into the new virtual environment "
                                          "using pip. All packages must be "
                                          "specified in a format "
                                          "understandable to pip.")
            self.parser.add_argument("-r",
                                     type=str,
                                     default=None,
                                     metavar="<requirements>",
                                     dest="requirements_file",
                                     help="Requirements file for dependency "
                                          "installation in the newly created "
                                          "virtual environment.")
            self.parser.add_argument("--pip-options",
                                     nargs="*",
                                     default=None,
                                     help="Comma- or space-separated list of "
                                          "command line options for "
                                          "dependency installation in the "
                                          "created virtual environment "
                                          "using `pip install`. To get a "
                                          "comprehensive list of options, "
                                          "run `python -m pip install -h`.",
                                     metavar="<pip-options>")
        elif subcommand == "uninstall":
            self.parser.add_argument("identifier",
                                     metavar="<identifier>",
                                     help="Information that uniquely "
                                          "identifies the environment. "
                                          "Can be name, checked out "
                                          "commit, branch name, directory, "
                                          "or custom user-defined tags.")
            self.parser.add_argument("packages",
                                     nargs="+",
                                     metavar="<packages>",
                                     help="Package dependencies to uninstall "
                                          "from the benchmarking environment "
                                          "using pip. All packages must be "
                                          "specified in a format "
                                          "understandable to pip.")
            self.parser.add_argument("--pip-options",
                                     nargs="*",
                                     default=None,
                                     help="Comma- or space-separated list "
                                          "of command line options for "
                                          "dependency removal in the "
                                          "benchmarking environment "
                                          "using `pip uninstall`. To get a "
                                          "comprehensive list of options, "
                                          "run `python -m pip uninstall -h`.",
                                     metavar="<pip-options>")
        elif subcommand == "list":
            pass
        elif subcommand == "update":
            pass

    def create(self, options: argparse.Namespace, verbose: bool):
        env_store = EnvironmentStore(config=self.config, verbose=verbose)
        env_store.create(options=options)

        return SUCCESS

    def delete(self, options: argparse.Namespace, verbose: bool):
        env_store = EnvironmentStore(config=self.config, verbose=verbose)
        env_store.delete(options=options)

        return SUCCESS

    def install(self, options: argparse.Namespace, verbose: bool):
        builder: PythonEnvBuilder = get_builder_class(config=self.config)

        env_store = EnvironmentStore(config=self.config, verbose=verbose)
        target_env = env_store.get(options.identifier)
        builder.install_packages(
            spec=target_env.python,
            packages=options.packages,
            requirements_file=options.requirements_file,
            options=options.pip_options,
            verbose=verbose)

        return SUCCESS

    def uninstall(self, options: argparse.Namespace, verbose: bool):
        builder: PythonEnvBuilder = get_builder_class(config=self.config)

        env_store = EnvironmentStore(config=self.config, verbose=verbose)
        target_env = env_store.get(options.identifier)
        builder.uninstall_packages(
            spec=target_env.python,
            packages=options.packages,
            options=options.pip_options,
            verbose=verbose)

        return SUCCESS

    def list(self, options: argparse.Namespace, verbose: bool):
        env_store = EnvironmentStore(config=self.config, verbose=verbose)
        env_store.list()
        return SUCCESS

    def update(self, options: argparse.Namespace, verbose: bool):
        raise PybmError("env updating is not implemented yet.")

    def run(self, args: List[str]):
        logger.debug("Running command: \"{cmd}\"".format(
            cmd=self.format_call(args)))

        subcommand_handlers = {
            "create": self.create,
            "delete": self.delete,
            "install": self.install,
            "uninstall": self.uninstall,
            "list": self.list,
            "update": self.update,
        }
        if not args or args[0] not in subcommand_handlers:
            self.parser.print_help()
            return ERROR

        subcommand, *args = args

        self.add_arguments(subcommand=subcommand)

        options = self.parser.parse_args(args)

        verbose: bool = options.verbose

        return subcommand_handlers[subcommand](options, verbose)
