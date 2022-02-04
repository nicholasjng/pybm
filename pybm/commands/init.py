from pathlib import Path
from typing import List

from pybm.command import CLICommand
from pybm.config import PybmConfig, LOCAL_CONFIG, GLOBAL_CONFIG
from pybm.env_store import EnvironmentStore
from pybm.exceptions import PybmError
from pybm.status_codes import SUCCESS
from pybm.util.git import is_main_worktree
from pybm.util.path import get_filenames


class InitCommand(CLICommand):
    """
    Initialize pybm in a git repository by adding a configuration file
    and an environment list into a directory.
    """

    usage = "pybm init [<options>]\n"

    def __init__(self):
        super(InitCommand, self).__init__(name="init")

    def add_arguments(self):
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
            "for the new pybm configuration file. Supplied arguments need to have the "
            "form 'key=value'. For a comprehensive list of configuration options, "
            "run `pybm config list`.",
        )
        self.parser.add_argument(
            "--skip-global",
            action="store_true",
            default=False,
            help="Skip applying system-wide defaults set in the global config file to "
            "the newly created pybm configuration.",
        )

    def run(self, args: List[str]) -> int:
        self.add_arguments()

        options = self.parser.parse_args(args)

        verbose: bool = options.verbose
        skip_global: bool = options.skip_global
        overrides: List[str] = options.overrides or []

        if verbose:
            print(f"Parsed command line options: {options}")

        if not is_main_worktree(Path.cwd()):
            raise PybmError(
                "Cannot initialize pybm: current directory is not a git repository."
            )

        local_config = PybmConfig()

        if Path(GLOBAL_CONFIG).exists() and not skip_global:
            global_config = PybmConfig.load(GLOBAL_CONFIG)
            for k, v in global_config.items():
                if v is not None:
                    if verbose:
                        print(f"Setting global config value {k} = {v}.")
                    local_config.set_value(k, v)

        for override in overrides:
            try:
                attr, value = override.split("=", maxsplit=2)
            except ValueError:
                raise PybmError(
                    "Config overrides need to be specified in the form 'attr=value'."
                )

            if verbose:
                print(f"Overriding config option {attr!r} with value {value!r}.")

            local_config.set_value(attr, value)

        for cfg in [GLOBAL_CONFIG, LOCAL_CONFIG]:
            config_dir = Path(cfg).parent
            config_dir.mkdir(parents=False, exist_ok=True)

        if options.remove_existing:
            for p in get_filenames(config_dir, file_ext=".toml"):
                (config_dir / p).unlink()

        if Path(LOCAL_CONFIG).exists():
            raise PybmError(
                "Configuration file already exists. If you want to write a new "
                "configuration file, run `pybm init --rm`."
            )

        local_config.save()

        env_store = EnvironmentStore(
            config=local_config, verbose=verbose, missing_ok=True
        )

        env_store.sync()

        return SUCCESS
