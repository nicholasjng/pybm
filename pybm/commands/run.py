from pathlib import Path
from typing import List, Union

from pybm.command import CLICommand
from pybm.config import PybmConfig, get_runner_class
from pybm.runners.runner import BenchmarkRunner
from pybm.util.common import lmap
from pybm.env_store import EnvironmentStore
from pybm.exceptions import PybmError
from pybm.util.path import list_contents
from pybm.status_codes import SUCCESS, ERROR


class RunCommand(CLICommand):
    """
    Run pybm benchmark workloads in specified environments.
    """
    usage = "pybm run <benchmark> <environment(s)> [<options>]\n"

    def __init__(self, name: str):
        super(RunCommand, self).__init__(name=name)
        config = PybmConfig.load(".pybm/config.yaml")
        runner_class = get_runner_class(config)
        self.runner: BenchmarkRunner = runner_class(config)

    def add_arguments(self):
        self.parser.add_argument("benchmarks",
                                 type=str,
                                 help="Name of the benchmark target(s) to "
                                      "run. Can be a single file, a directory "
                                      "or a glob expression. This should be "
                                      "a consistent file or location across "
                                      "different environments, otherwise "
                                      "results might not be comparable.",
                                 metavar="<benchmark>")
        self.parser.add_argument("environments",
                                 nargs="*",
                                 default=None,
                                 help="Environments to run the benchmarks "
                                      "in. If omitted, by default,"
                                      "benchmarks will be run in the "
                                      "main environment if no other "
                                      "environments exist outside of the main "
                                      "repository worktree, otherwise an "
                                      "error will be raised, unless the "
                                      "\"--all\" switch was used.",
                                 metavar="<environment(s)>")
        self.parser.add_argument("--all",
                                 action="store_true",
                                 default=False,
                                 help="Run specified benchmarks in all "
                                      "existing environments.")
        self.parser.add_argument("-o", "--out-dir",
                                 type=str,
                                 default=None,
                                 dest="out_dir",
                                 help="Output directory to store the results "
                                      "in.")
        self.parser.add_argument("--filter",
                                 type=str,
                                 default=None,
                                 dest="benchmark_filter",
                                 help="Regex filter to selectively run "
                                      "benchmarks inside the target files. "
                                      "Only benchmarks matching the given "
                                      "filter will be run.")

    def run(self, args: List[str]) -> int:
        if not args:
            self.parser.print_help()
            return ERROR

        self.add_arguments()
        options = self.parser.parse_args(args)

        verbose: bool = options.verbose
        env_ids: list[str] = options.environments or []
        run_all: bool = options.all
        benchmark_filter = options.benchmark_filter

        benchmark_path = Path(options.benchmarks)
        if benchmark_path.is_absolute():
            raise PybmError(f"Benchmark path {benchmark_path} was given in "
                            f"absolute form. Please specify the targets "
                            f"by a path relative to the workspace "
                            f"root to enable running benchmarks "
                            f"in multiple environments.")

        with EnvironmentStore(".pybm/envs.yaml", verbose) as env_store:
            if len(env_ids) == 0 and len(env_store.environments) > 1:
                raise PybmError("No environments were specified as "
                                "positional arguments to `pybm run`, "
                                "but more than one environment exists in the "
                                "current repository. Please specify your "
                                "desired target environments specifically on "
                                "the command line.")
            if len(env_ids) == 0 or run_all:
                target_envs = env_store.environments
            else:
                # TODO: Get envs by attributes other than name
                attr = "name"
                target_envs = [env_store.get(attr, val) for val in env_ids]

        for env in target_envs:
            print(f"Starting benchmarking run in environment {env.name!r}.")
            # join relative path with workspace root
            path = Path(env.workspace.root) / benchmark_path
            print("Discovering benchmark targets.....", end="")
            # attempting to discover identifier in workspace
            if benchmark_path.is_dir():
                benchmarks = list_contents(path, file_suffix=".py")
            elif benchmark_path.is_file():
                benchmarks = list(str(path))
            elif is_glob_expression(benchmark_path):
                benchmarks = lmap(
                    str,
                    path.parent.glob(benchmark_path.name)
                )
            else:
                benchmarks = []
            print("failed.") if not benchmarks else print("done.")
            num_benchmarks = len(benchmarks)
            if num_benchmarks == 0:
                print(f"Benchmark selector {benchmark_path} "
                      f"did not match any directories or "
                      f"Python files in environment {env.name!r}.")
                if self.runner.fail_fast:
                    print("Error: Aborting benchmark run because fast "
                          "failure mode is enabled.")
                    return ERROR
                else:
                    continue
            print(f"Found a total of {num_benchmarks} benchmark targets.")
            self.runner.run_benchmarks(benchmarks=benchmarks,
                                       environment=env,
                                       benchmark_filter=benchmark_filter,
                                       context_providers=None)
        print("Finished benchmarking in all specified environments.")
        return SUCCESS


def is_glob_expression(expr: Union[str, Path]) -> bool:
    return "*" in str(expr)
