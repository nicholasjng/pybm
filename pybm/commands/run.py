import json
from pathlib import Path
from typing import List

from pybm.command import CLICommand
from pybm.config import PybmConfig, get_runner_class
from pybm.env_store import EnvironmentStore
from pybm.exceptions import PybmError
from pybm.runners.runner import BenchmarkRunner
from pybm.runners.util import create_subdir, create_rundir
from pybm.status_codes import SUCCESS, ERROR


class RunCommand(CLICommand):
    """
    Run pybm benchmark workloads in specified environments.
    """
    usage = "pybm run <benchmark> <environment(s)> [<options>]\n"

    def __init__(self):
        super(RunCommand, self).__init__(name="run")
        config = PybmConfig.load(".pybm/config.yaml")
        self.runner: BenchmarkRunner = get_runner_class(config)

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
        self.parser.add_argument("--all",
                                 action="store_true",
                                 default=False,
                                 dest="run_all",
                                 help="Run specified benchmarks in all "
                                      "existing pybm environments.")
        self.parser.add_argument("--filter",
                                 type=str,
                                 default=None,
                                 dest="benchmark_filter",
                                 help="Regex filter to selectively run "
                                      "benchmarks inside the target files. "
                                      "Only benchmarks matching the given "
                                      "filter will be run.")
        self.parser.add_argument("--repetitions",
                                 type=int,
                                 default=5,
                                 metavar="<reps>",
                                 help="Number of repetitions for the target "
                                      "benchmarks. Repeating benchmarks"
                                      "can boost confidence about the"
                                      "statistical significance of "
                                      "performance differences between "
                                      "different environments.")
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

        verbose: bool = options.verbose
        env_ids: list[str] = options.environments or []
        run_all: bool = options.run_all

        result_dir = create_rundir(self.runner.result_dir)
        benchmark_path = Path(options.benchmarks)

        if benchmark_path.is_absolute():
            raise PybmError(f"Benchmark path {benchmark_path} was given in "
                            f"absolute form. Please specify the targets "
                            f"by a path relative to the worktree root to"
                            f"enable running benchmarks in multiple "
                            f"environments.")

        with EnvironmentStore(".pybm/envs.yaml", verbose) as env_store:
            if len(env_ids) == 0:
                if not run_all and len(env_store.environments) > 1:
                    raise PybmError("No environments were specified as "
                                    "positional arguments to `pybm run`, "
                                    "but more than one environment exists "
                                    "in the current repository. Please "
                                    "supply your desired target environments "
                                    "specifically when calling `pybm run`.")
                if run_all:
                    target_envs = env_store.environments
            else:
                # TODO: Find envs by attributes other than name
                attr = "name"
                target_envs = [env_store.get(attr, val) for val in env_ids]

        for environment in target_envs:
            self.runner.check_required_packages(environment=environment)
            subdir = create_subdir(result_dir=result_dir,
                                   environment=environment)
            print(f"Starting benchmarking run in environment "
                  f"{environment.name!r}.")
            # join relative path with worktree root
            path = Path(environment.get_value("worktree.root")
                        ) / benchmark_path
            print(f"Discovering benchmark targets in "
                  f"environment {environment.name!r}.....", end="")
            # attempting to discover identifier in worktree
            benchmark_targets = self.runner.find_targets(path=path)
            print("failed.") if not benchmark_targets else print("done.")
            # stupid name, only used for printing below
            n = len(benchmark_targets)
            if n > 0:
                print(f"Found a total of {n} benchmark targets for "
                      f"environment {environment.name!r}.")
                for i, benchmark in enumerate(benchmark_targets):
                    print(f"Running benchmark {benchmark}.....[{i + 1}/{n}]")
                    rc, data = self.runner.dispatch(
                        benchmark=benchmark,
                        environment=environment,
                        repetitions=options.repetitions,
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
            else:
                msg = f"Benchmark selector {benchmark_path!r} did not match " \
                      f"any directories or Python files in environment " \
                      f"{environment.name!r}."
                if self.runner.fail_fast:
                    error_msg = "Aborted benchmarking run because fast " \
                                "failure mode was enabled."
                    raise PybmError("\n".join([msg, error_msg]))
                else:
                    print("Warning: " + msg)
            print(f"Finished benchmarking run in environment "
                  f"{environment.name!r}.")
        print("Finished benchmarking in all specified environments.")
        return SUCCESS
