import sys
from typing import List

from pybm.command import CLICommand
from pybm.config import config
from pybm.exceptions import PybmError
from pybm.git import GitWorktreeWrapper
from pybm.logging import get_logger
from pybm.mixins.filemanager import WorkspaceManagerContextMixin
from pybm.statuscodes import ERROR, SUCCESS
from pybm.venv import PythonVenv
from pybm.workspace import Workspace

logger = get_logger(__name__)


class CreateCommand(WorkspaceManagerContextMixin, CLICommand):
    """
    Create a pybm benchmark workspace.
    """

    usage = "pybm create <commit-ish> <name> <dest> [<options>]\n"

    def __init__(self):
        super().__init__(name="create")

        # git worktree wrapper and builder class
        self.git_worktree = GitWorktreeWrapper()

        # relevant config attributes
        self.datefmt = config.get_value("core.datefmt")

    def add_arguments(self):
        self.parser.add_argument(
            "commit_ish",
            metavar="<commit-ish>",
            help="Commit, branch or tag to create a benchmark workspace for. A git "
            "worktree will be created for the given reference.",
        )
        self.parser.add_argument(
            "name",
            metavar="<name>",
            nargs="?",
            default=None,
            help="Unique name for the created workspace. Can be used to "
            "reference workspaces from the command line.",
        )
        self.parser.add_argument(
            "destination",
            metavar="<dest>",
            nargs="?",
            default=None,
            help="Destination directory of the new git worktree. Defaults to "
            "repository-name@{commit|branch|tag}.",
        )
        self.parser.add_argument(
            "--create-branch",
            type=str,
            default=None,
            metavar="<name>",
            help="Create a branch with name <name> and HEAD <commit-ish> from the "
            "given git reference.",
        )
        self.parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            default=False,
            help="Force worktree creation. Useful for checking out a branch "
            "multiple times with different custom requirements.",
        )
        self.parser.add_argument(
            "--resolve-commits",
            action="store_true",
            default=False,
            help="Always resolve the given git ref to its associated commit. "
            "If the given ref is a branch name, this detaches the HEAD "
            "(see https://git-scm.com/docs/git-checkout#_detached_head).",
        )
        self.parser.add_argument(
            "--no-checkout",
            action="store_true",
            default=False,
            help="Skip worktree checkout after creation. Useful for sparsely "
            "checking out branches.",
        )
        self.parser.add_argument(
            "--link-existing",
            type=str,
            default=None,
            dest="link_dir",
            metavar="<path>",
            help="Link an existing Python virtual environment directory to the new "
            "workspace.",
        )
        self.parser.add_argument(
            "--no-install",
            action="store_true",
            default=False,
            help="Skip project installation at the chosen git reference.",
        )
        self.parser.add_argument(
            "--no-deps",
            action="store_true",
            default=False,
            help="Do not install project dependencies.",
        )
        self.parser.add_argument(
            "--python",
            type=str,
            default=sys.executable,
            dest="executable",
            help="Python interpreter to use for virtual environment creation.",
            metavar="<python>",
        )
        self.parser.add_argument(
            "--create-option",
            default=list(),
            action="append",
            metavar="<option>",
            dest="create_options",
            help="Additional creation options passed to Python's venv. "
            "Can be used multiple times to supply multiple options.",
        )
        self.parser.add_argument(
            "--install-option",
            default=list(),
            action="append",
            metavar="<option>",
            dest="install_options",
            help="Additional installation options passed to `pip install`. "
            "Can be used multiple times to supply multiple options.",
        )
        self.parser.add_argument(
            "--extra-packages",
            default=list(),
            action="append",
            metavar="<pkg-name>",
            help="Additional packages to install into the created benchmark workspace.",
        )

    def run(self, args: List[str]):
        logger.debug(f"Running command `{self.format_call(args)}`.")

        if not args:
            self.parser.print_help()
            return ERROR

        self.add_arguments()

        options = self.parser.parse_args(args)

        # verbosity
        verbose: bool = options.verbose

        # git worktree info
        commit_ish: str = options.commit_ish
        name: str = options.name

        with self.main_context(verbose=verbose, readonly=False):
            if name in self.workspaces:
                raise PybmError(f"Workspace {name!r} already exists.")

            worktree, venv = None, None
            try:
                worktree = self.git_worktree.add(
                    commit_ish=commit_ish,
                    destination=options.destination,
                    create_branch=options.create_branch,
                    force=options.force,
                    checkout=not options.no_checkout,
                    resolve_commits=options.resolve_commits,
                )

                name = name or f"workspace_{len(self.workspaces) + 1}"

                # either create venv in worktree or link from outside
                if options.link_dir is not None:
                    in_tree, directory = False, options.link_dir
                else:
                    in_tree, directory = True, worktree.root

                venv = PythonVenv(
                    directory=directory,
                    executable=options.executable,
                ).create(options=options.create_options, in_tree=in_tree)

                if not options.no_install:
                    venv.install(
                        directory=worktree.root,
                        with_dependencies=not options.no_deps,
                        extra_packages=options.extra_packages,
                        options=options.install_options,
                        verbose=verbose,
                    )

                workspace = Workspace(name=name, worktree=worktree, venv=venv)
                self.workspaces[name] = workspace

                print(
                    f"Successfully created workspace {name!r} with ref {commit_ish!r}."
                )
            except PybmError:
                if in_tree and venv is not None:
                    venv.delete()
                if worktree is not None:
                    self.git_worktree.remove(worktree.root, verbose=verbose)

        return SUCCESS
