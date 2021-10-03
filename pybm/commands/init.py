import sys
from datetime import datetime
from pathlib import Path
from typing import List

from pybm.builders import PythonEnvBuilder
from pybm.command import CLICommand
from pybm.config import PybmConfig, get_builder_class
from pybm.env_store import EnvironmentStore
from pybm.exceptions import PybmError
from pybm.git import GitWorktreeWrapper
from pybm.status_codes import SUCCESS
from pybm.util.git import is_main_worktree


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
            builder_class: PythonEnvBuilder = get_builder_class(config)
            git: GitWorktreeWrapper = GitWorktreeWrapper(config)
            for i, worktree in enumerate(git.list_worktrees()):
                venv_root = Path(worktree.root) / "venv"
                if venv_root.exists() and venv_root.is_dir():
                    python_spec = builder_class.link_existing(venv_root,
                                                              verbose=verbose)
                else:
                    python_spec = builder_class.create(sys.executable,
                                                       venv_root)
                    # TODO: Enable auto-grabbing from venv home
                created = datetime.now()
                fmt = config.get_value("core.datetimeFormatter")
                # TODO: Assert that the main worktree is "root"
                env_store.create(name="root" if i == 0 else f"env_{i + 1}",
                                 worktree=worktree,
                                 python=python_spec,
                                 created=created.strftime(fmt))

    def run(self, args: List[str]) -> int:
        self.add_arguments()

        options = self.parser.parse_args(args)

        verbose: bool = options.verbose
        if verbose:
            print(f"Parsed command line options: {options}")

        if not is_main_worktree(Path.cwd()):
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
