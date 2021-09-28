from pathlib import Path
from datetime import datetime
from typing import List

from pybm.command import CLICommand
from pybm.config import PybmConfig, get_builder_class
from pybm.env_store import EnvironmentStore
from pybm.exceptions import PybmError
from pybm.git import git
from pybm.util.git import is_git_repository
from pybm.util.path import get_subdirs
from pybm.status_codes import SUCCESS


class InitCommand(CLICommand):
    """
    Initialize pybm in a git repository by adding a configuration file
    and an environment list into a directory.
    """
    usage = "pybm init <config-dir> [<options>]\n"

    def __init__(self):
        super(InitCommand, self).__init__(name="init")

    def add_arguments(self):
        self.parser.add_argument("config_dir",
                                 type=str,
                                 nargs="?",
                                 default=".pybm",
                                 metavar="<config-dir>",
                                 help="Directory in which to store the pybm "
                                      "configuration data.")
        self.parser.add_argument("--rm",
                                 action="store_true",
                                 default=False,
                                 dest="remove_existing",
                                 help="Overwrite existing configuration.")

    @staticmethod
    def discover_existing_environments(cfg_path: Path, env_path: Path,
                                       verbose: bool = False):
        with EnvironmentStore(env_path, verbose, True) as env_store:
            config = PybmConfig.load(cfg_path)
            builder_class = get_builder_class(config)
            for i, workspace in enumerate(git.list_worktrees()):
                if "venv" in get_subdirs(workspace.root):
                    venv_root = Path(workspace.root) / "venv"
                    venv = builder_class(config).link_existing(venv_root,
                                                               verbose=verbose)
                else:
                    # TODO: Enable auto-grabbing from venv home
                    raise PybmError(f"Virtual environment not found "
                                    f"for environment with root "
                                    f"{workspace.root!r}.")
                created = datetime.now()
                fmt = config.get_value("core.datetimeFormatter")
                env_store.create(name="root" if i == 0 else f"env_{i + 1}",
                                 workspace=workspace,
                                 venv=venv,
                                 created=created.strftime(fmt))

    def run(self, args: List[str]) -> int:
        self.add_arguments()

        options = self.parser.parse_args(args)

        verbose: bool = options.verbose
        if verbose:
            print(f"Parsed command line options: {options}")

        if not is_git_repository(Path.cwd()):
            raise PybmError("Cannot initialize Pybm here because the "
                            "current directory was not recognized "
                            "as a git repository.")

        config_dir = Path(options.config_dir)
        config_path = config_dir / "config.yaml"
        env_path = config_dir / "envs.yaml"
        config_dir.mkdir(parents=True, exist_ok=True)
        if options.remove_existing:
            for p in [config_path, env_path]:
                p.unlink(missing_ok=True)
        if config_path.exists():
            raise PybmError("Configuration file already exists. "
                            "If you want to write a new config file, "
                            "please specify the \"--rm\" option "
                            "to `pybm init`.")
        else:
            PybmConfig().save(config_path)

        self.discover_existing_environments(config_path, env_path,
                                            verbose=verbose)
        return SUCCESS