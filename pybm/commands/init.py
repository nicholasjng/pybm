from pathlib import Path
from typing import List

from pybm.command import CLICommand
from pybm.config import PybmConfig
from pybm.env_store import EnvironmentStore
from pybm.exceptions import PybmError
from pybm.status_codes import SUCCESS
from pybm.util.git import is_main_worktree
from pybm.util.path import list_contents


class InitCommand(CLICommand):
    """
    Initialize pybm in a git repository by adding a configuration file
    and an environment list into a directory.
    """

    usage = "pybm init <config-dir> [<options>]\n"

    def __init__(self):
        super(InitCommand, self).__init__(name="init")

    def add_arguments(self):
        self.parser.add_argument(
            "config_dir",
            type=str,
            nargs="?",
            default=".pybm",
            metavar="<config-dir>",
            help="Directory in which to store the pybm configuration data.",
        )

        self.parser.add_argument(
            "--rm",
            action="store_true",
            default=False,
            dest="remove_existing",
            help="Overwrite existing configuration.",
        )

        self.parser.add_argument(
            "-o",
            "--override",
            action="append",
            dest="overrides",
            help="Override a specific configuration setting with a custom value "
            "for the new pybm configuration file. Supplied arguments need "
            "to have the form 'key=value'. For a comprehensive list of "
            "configuration options, run `pybm config list`.",
        )

    def run(self, args: List[str]) -> int:
        self.add_arguments()

        options = self.parser.parse_args(args)

        verbose: bool = options.verbose
        overrides: List[str] = options.overrides or []

        if verbose:
            print(f"Parsed command line options: {options}")

        if not is_main_worktree(Path.cwd()):
            raise PybmError(
                "Cannot initialize pybm: current directory is not a git repository."
            )

        config = PybmConfig()

        for override in overrides:
            try:
                attr, value = override.split("=", maxsplit=2)
            except ValueError:
                raise PybmError(
                    "Config overrides need to be specified in the form 'attr=value'."
                )

            if verbose:
                print(f"Overriding config option {attr!r} with value {value!r}.")

            config.set_value(attr, value)

        config_dir = Path(options.config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.toml"

        if options.remove_existing:
            for p in list_contents(config_dir, file_suffix=".toml", names_only=True):
                (config_dir / p).unlink()

        if config_path.exists():
            raise PybmError(
                "Configuration file already exists. "
                "If you want to write a new config file, "
                "please specify the '--rm' option to `pybm init`."
            )
        else:
            config.save(config_path)

        env_store = EnvironmentStore(config=config, verbose=verbose, missing_ok=True)

        env_store.sync()

        return SUCCESS
