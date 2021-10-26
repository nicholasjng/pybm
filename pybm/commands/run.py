import json
import warnings
from pathlib import Path
from typing import List, Optional

from pybm.command import CLICommand
from pybm.config import PybmConfig, get_runner_class
from pybm.env_store import EnvironmentStore
from pybm.exceptions import PybmError
from pybm.runners.base import BenchmarkRunner
from pybm.runners.util import create_subdir, create_rundir, discover_targets
from pybm.status_codes import SUCCESS, ERROR


class RunCommand(CLICommand):
    """
    Run pybm benchmark workloads in specified environments.
    """
    usage = "pybm run <benchmark> <environment(s)> [<options>]\n"

    def __init__(self):
        super(RunCommand, self).__init__(name="run")
        self.config = PybmConfig.load(".pybm/config.yaml")

    def add_arguments(self):
        self.parser.add_argument("benchmarks",
                                 type=str,
                                 help="Name of the benchmark target(s) to "
                                      "run. Can be a path to a single file, "
                                      "a directory, or a glob expression. "
                                      "Given paths need to be relative to "
                                      "the worktree root.",
                                 metavar="<benchmark>")
        self.parser.add_argument("environments",
                                 nargs="*",
                                 default=None,
                                 help="Environments to run the benchmarks "
                                      "in. If omitted, by default, "
                                      "benchmarks will be run in the "
                                      "main environment if only one "
                                      "environment exists, otherwise an "
                                      "error will be raised, unless the "
                                      "\"--all\" switch is used.",
                                 metavar="<environment(s)>")
        self.parser.add_argument("-m",
                                 action="store_true",
                                 default=False,
                                 dest="run_as_module",
                                 help="Run benchmark targets as modules. "
                                      "This is the preferred option if you "
                                      "are benchmarking code outside of a "
                                      "package.")
        self.parser.add_argument("--checkouts",
                                 action="store_true",
                                 default=False,
                                 help="Run benchmarks in checkout mode in "
                                      "environment \"root\". Here, instead "
                                      "of using checked out physical "
                                      "worktrees, the benchmarks are run with "
                                      "`git checkout` commands. Use this if "
                                      "you do not have any changing "
                                      "requirements in between benchmarks.")
        self.parser.add_argument("-A", "--all",
                                 action="store_true",
                                 default=False,
                                 dest="run_all",
                                 help="Run specified benchmarks in all "
                                      "existing pybm environments.")
        self.parser.add_argument("-S", "--source",
                                 type=str,
                                 default=None,
                                 dest="benchmark_source",
                                 metavar="<git-ref>",
                                 help="Optionally source benchmark targets "
                                      "from a different git reference. "
                                      "Useful when benchmarking library code "
                                      "with a custom benchmark suite.")
        self.parser.add_argument("--repetitions",
                                 type=int,
                                 default=5,
                                 metavar="<reps>",
                                 help="Number of repetitions for the target "
                                      "benchmarks. Repeating benchmarks"
                                      "can boost confidence about the"
                                      "statistical significance of "
                                      "performance differences between "
                                      "different implementations.")
        self.parser.add_argument("--filter",
                                 type=str,
                                 default=None,
                                 dest="benchmark_filter",
                                 help="Regex used to selectively run "
                                      "benchmarks inside the target files "
                                      "matching the given expression.")
        self.parser.add_argument("--context",
                                 action="append",
                                 default=None,
                                 dest="benchmark_context",
                                 metavar="<context>",
                                 help="Additional global context that is "
                                      "constant across environments, "
                                      "given as strings in the format"
                                      "--context='key'='value'. Use this "
                                      "option to save additional, unchanging "
                                      "information such as processor"
                                      "architecture, clock speed, or other "
                                      "system info. Keys must be "
                                      "unique, attempts to supply two "
                                      "context values for the same key "
                                      "results in an error. For logging "
                                      "environment-specific context values, "
                                      "use Python context providers instead "
                                      "by setting the runner.contextProviders "
                                      "config option.")

    def run(self, args: List[str]) -> int:
        if not args:
            self.parser.print_help()
            return ERROR

        self.add_arguments()
        options = self.parser.parse_args(args)

        runner: BenchmarkRunner = get_runner_class(config=self.config)

        verbose: bool = options.verbose
        env_ids: list[str] = options.environments or []
        run_all: bool = options.run_all
        checkout_mode: bool = options.checkouts
        source_ref: Optional[str] = options.benchmark_source
        source_path = Path(options.benchmarks)

        result_dir = create_rundir(runner.result_dir)

        if source_path.is_absolute():
            raise PybmError(f"Benchmark path {source_path} was given in "
                            f"absolute form. Please specify the targets "
                            f"by a path relative to the worktree root to"
                            f"enable running benchmarks in multiple "
                            f"environments.")

        env_store = EnvironmentStore(config=self.config, verbose=verbose)

        if len(env_ids) > 0:
            if run_all:
                raise PybmError("The -A/--all switch can only be used as a "
                                "substitute for specific environment IDs, but "
                                "the following environments were requested:"
                                f"{', '.join(env_ids)}. Please either omit "
                                f"the -A/-all switch or the specific "
                                f"environment IDs.")
        else:
            if checkout_mode:
                raise PybmError(
                    "When running in checkout mode, please specify at "
                    "least one valid git reference to benchmark. To "
                    "benchmark the current checkout "
                    "in the \"root\" environment, use the command "
                    f"`pybm run {source_path} root`.")
            if not run_all and len(env_store.environments) > 1:
                raise PybmError("No environments were specified as "
                                "positional arguments to `pybm run`, "
                                "but more than one environment exists "
                                "in the current repository. Please "
                                "supply your desired target environments "
                                "specifically when calling `pybm run`, or "
                                "use the -A/--all switch.")

        if run_all:
            env_ids = [env.name for env in env_store.environments]

        for env_id in env_ids:
            if checkout_mode:
                environment = env_store.get("root")
                # check out given reference
                environment.worktree.switch(ref=env_id)
            else:
                environment = env_store.get(env_id)

            runner.check_required_packages(environment=environment)
            subdir = create_subdir(result_dir=result_dir,
                                   worktree=environment.worktree)

            with discover_targets(worktree=environment.worktree,
                                  source_path=source_path,
                                  source_ref=source_ref) as benchmark_targets:
                n = len(benchmark_targets)
                if n > 0:
                    print(f"Found a total of {n} benchmark targets for "
                          f"environment {environment.name!r}.")
                else:
                    msg = f"Benchmark selector {source_path!r} did not " \
                          f"match any directory or Python files in " \
                          f"environment {environment.name!r}."
                    if runner.fail_fast:
                        error_msg = "Aborted benchmark run because " \
                                    "fast failure mode was enabled."
                        raise PybmError("\n".join([msg, error_msg]))
                    else:
                        warnings.warn(msg)
                        continue

                for i, benchmark in enumerate(benchmark_targets):
                    print(f"Running benchmark {benchmark}.....[{i + 1}/{n}]")
                    rc, data = runner.dispatch(
                        benchmark=benchmark,
                        environment=environment,
                        repetitions=options.repetitions,
                        run_as_module=options.run_as_module,
                        benchmark_filter=options.benchmark_filter,
                        benchmark_context=options.benchmark_context)
                    # TODO: Switch this to a general IO Connector later
                    if rc != 0:
                        raise PybmError("Something went wrong.")
                    else:
                        result_name = Path(benchmark).stem + "_results.json"
                        result_file = subdir / result_name
                        with open(result_file, "w") as res:
                            json.dump(json.loads(data), res)
        print("Finished benchmarking in all specified environments.")
        return SUCCESS
