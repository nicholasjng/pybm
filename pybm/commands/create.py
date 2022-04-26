import sys
from pathlib import Path

# from datetime import datetime
from typing import List

from pybm.config import config, get_component_class
from pybm.providers import BaseProvider
from pybm.command import CLICommand
from pybm.git import GitWorktreeWrapper, GitWorktree
from pybm.logging import get_logger
from pybm.mixins.filemanager import WorkspaceManagerContextMixin
from pybm.providers.util import get_venv_root
from pybm.specs import PythonSpec
from pybm.status_codes import ERROR, SUCCESS
from pybm.workspace import Workspace

logger = get_logger(__name__)


def cleanup_venv(builder: BaseProvider, worktree: GitWorktree, spec: PythonSpec):
    print("Cleaning up created virtual environment after exception.")

    root = get_venv_root(spec.executable)

    # venv is embedded into the worktree
    if Path(root).parent == Path(worktree.root):
        builder.delete(spec)
    else:
        print(f"Did not tear down linked venv with root {root}.")


def cleanup_worktree(git_worktree: GitWorktreeWrapper, worktree: GitWorktree):
    print("Cleaning up created worktree after exception.")
    git_worktree.remove(info=worktree.root)


class CreateCommand(WorkspaceManagerContextMixin, CLICommand):
    """
    Create a pybm benchmark workspace.
    """

    usage = "pybm create <commit-ish> <name> <dest> [<options>]\n"

    def __init__(self):
        super().__init__(name="create")

        # git worktree wrapper and builder class
        self.git_worktree = GitWorktreeWrapper()
        self.provider = get_component_class("provider")

        # relevant config attributes
        self.datefmt = config.get_value("core.datefmt")

    def add_arguments(self):
        self.parser.add_argument(
            "commit_ish",
            metavar="<commit-ish>",
            help="Commit, branch or tag to create a benchmark workspace for. A git "
            "worktree will be created for the given git reference.",
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
            default="",
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
            "--provider",
            type=str,
            default=None,
            choices=("stdlib",),
            metavar="<provider>",
            help="Python provider to use for virtual environment setup.",
        )
        self.parser.add_argument(
            "-L",
            "--link-existing",
            type=str,
            default=None,
            dest="link_dir",
            metavar="<path/to/venv>",
            help="Link an existing Python virtual environment to the created pybm "
            "workspace. Raises an error if the path does not exist or is not "
            "recognized as a valid Python virtual environment.",
        )
        self.parser.add_argument(
            "--skip-project-install",
            dest="no_install_project",
            action="store_false",
            default=True,
            help="Skip project installation at the chosen git reference.",
        )
        self.parser.add_argument(
            "--python-version",
            type=str,
            default=sys.executable,
            dest="executable",
            help="Python interpreter used for virtual environment creation with venv.",
            metavar="<python>",
        )
        self.parser.add_argument(
            "--create-option",
            default=list(),
            action="append",
            metavar="<create-option>",
            dest="create_options",
            help="Additional creation options passed to the Python provider. "
            "Can be used multiple times to supply multiple options. Applicable for "
            "providers using `python -m venv`.",
        )
        self.parser.add_argument(
            "--install-option",
            default=list(),
            action="append",
            metavar="<option>",
            dest="install_options",
            help="Additional installation options passed to the Python provider. "
            "Can be used multiple times to supply multiple options.",
        )
        self.parser.add_argument(
            "--extra-packages",
            default=None,
            action="append",
            metavar="<name>",
            help="Additional packages to install into the created benchmark workspace.",
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

        # git worktree info
        commit_ish: str = option_dict.pop("commit_ish")
        name: str = option_dict.pop("name")
        destination: str = option_dict.pop("destination")
        create_branch: str = option_dict.pop("create_branch")
        force: bool = option_dict.pop("force")
        checkout: bool = not option_dict.pop("no_checkout")
        resolve_commits: bool = option_dict.pop("resolve_commits")

        # Python env creation options
        create_options: List[str] = option_dict.pop("create_options")
        executable: str = option_dict.pop("executable")
        link_dir: str = option_dict.pop("link_dir")

        # Python env installation options
        install_project: bool = not option_dict.pop("no_install_project")
        install_options: List[str] = option_dict.pop("install_options")
        extra_packages: List[str] = option_dict.pop("extra_packages")

        provider: BaseProvider = option_dict.pop("provider")

        if not provider:
            provider = self.provider

        with self.main_context(verbose=verbose, readonly=False) as ctx:
            assert ctx is not None
            worktree = self.git_worktree.add(
                commit_ish=commit_ish,
                destination=destination,
                create_branch=create_branch,
                force=force,
                checkout=checkout,
                resolve_commits=resolve_commits,
            )

            ctx.callback(cleanup_worktree, self.git_worktree, worktree)

            if link_dir is not None:
                python_spec = provider.link(link_dir)
            else:
                python_spec = provider.create(
                    executable=executable,
                    destination=worktree.root,
                    options=create_options,
                    verbose=verbose,
                )

            ctx.callback(cleanup_venv, provider, worktree, python_spec)

            if worktree is not None and python_spec is not None:
                # pop all cleanups and re-push workspace file save to disk
                ctx.pop_all()
                ctx.callback(self.save)

            name = name or f"workspace_{len(self.workspaces) + 1}"

            # created = datetime.now().strftime(self.datefmt)

            workspace = Workspace(
                name=name,
                worktree=worktree,
                spec=python_spec,
            )

            if install_project:
                # install project along with dependencies
                provider.install(
                    workspace=workspace,
                    extra_packages=extra_packages,
                    options=install_options,
                    verbose=verbose,
                )

            self.workspaces[name] = workspace

            print(f"Successfully created benchmark workspace for ref {commit_ish!r}.")

        return SUCCESS
