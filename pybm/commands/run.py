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
        self.parser.add_argument(
            "benchmarks",
            type=str,
            help="Name of the benchmark target(s) to "
            "run. Can be a path to a single file, "
            "a directory, or a glob expression. "
            "Given paths need to be relative to "
            "the worktree root.",
            metavar="<benchmark>",
        )
        self.parser.add_argument(
            "environments",
            nargs="*",
            default=None,
            help="Environments to run the benchmarks "
            "in. If omitted, by default, "
            "benchmarks will be run in the "
            "main environment if only one "
            "environment exists, otherwise an "
            "error will be raised, unless the "
            '"--all" switch is used.',
            metavar="<environment(s)>",
        )
        self.parser.add_argument(
            "-m",
            action="store_true",
            default=False,
            dest="run_as_module",
            help="Run benchmark targets as modules. "
            "Use this to benchmark code "
            "outside of a package.",
        )
        self.parser.add_argument(
            "--checkout",
            action="store_true",
            default=False,
            help="Run benchmarks in checkout mode in "
            'environment "root". Here, instead of '
            "persisted git worktrees, different refs "
            "are benchmarked using `git checkout` commands.",
        )
        self.parser.add_argument(
            "-A",
            "--all",
            action="store_true",
            default=False,
            dest="run_all",
            help="Run specified benchmarks in all existing pybm environments.",
        )
        self.parser.add_argument(
            "-S",
            "--source",
            type=str,
            default=None,
            dest="benchmark_source",
            metavar="<git-ref>",
            help="Source benchmark targets from a different git reference.",
        )
        self.parser.add_argument(
            "--repetitions",
            type=int,
            default=5,
            metavar="<reps>",
            help="Number of repetitions for the target benchmarks.",
        )
        self.parser.add_argument(
            "--filter",
            type=str,
            default=None,
            dest="benchmark_filter",
            metavar="<regex>",
            help="Regular expression to selectively "
            "filter benchmarks by name in the target files.",
        )
        self.parser.add_argument(
            "--context",
            action="append",
            default=None,
            dest="benchmark_context",
            metavar="<context>",
            help="Additional global context, given "
            "as strings in the format"
            "--context='key'='value'. Keys must be "
            "unique, supplying two or more "
            "context values for the same key "
            "results in an error.",
        )

        runner: BenchmarkRunner = get_runner_class(config=self.config)
        runner_name = self.config.get_value("runner.className")
        runner_group_desc = (
            f"Additional options from configured benchmark runner {runner_name!r}"
        )
        runner_group = self.parser.add_argument_group(runner_group_desc)
        # add builder-specific options into the group
        for arg in runner.add_arguments():
            runner_group.add_argument(arg.pop("flags"), **arg)

    def run(self, args: List[str]) -> int:
        if not args:
            self.parser.print_help()
            return ERROR

        self.add_arguments()
        options = self.parser.parse_args(args)

        runner: BenchmarkRunner = get_runner_class(config=self.config)

        verbose: bool = options.verbose
        env_ids: List[str] = options.environments or []
        run_all: bool = options.run_all
        checkout_mode: bool = options.checkout
        source_ref: Optional[str] = options.benchmark_source
        source_path = Path(options.benchmarks)

        result_dir = create_rundir(runner.result_dir)

        if source_path.is_absolute():
            raise PybmError(
                f"Benchmark path {source_path!r} was given in "
                f"absolute form. Please specify the targets "
                f"by a path relative to the worktree root to"
                f"enable running benchmarks in multiple "
                f"environments."
            )

        env_store = EnvironmentStore(config=self.config, verbose=verbose)

        if len(env_ids) > 0:
            if run_all:
                raise PybmError(
                    "The -A/--all switch can only be used as a "
                    "substitute for specific environment IDs, but "
                    "the following environments were requested: "
                    f"{', '.join(env_ids)}. Please either omit "
                    f"the -A/-all switch or the specific "
                    f"environment IDs."
                )
        else:
            if checkout_mode:
                raise PybmError(
                    "When running in checkout mode, please specify at "
                    "least one valid git reference to benchmark. To "
                    "benchmark the current checkout in the "
                    '"root" environment, use the command '
                    f"`pybm run {source_path} root`."
                )

            if not run_all and len(env_store.environments) > 1:
                raise PybmError(
                    "No environments were specified as "
                    "positional arguments to `pybm run`, "
                    "but more than one environment exists "
                    "in the current repository. Please "
                    "supply your desired target environments "
                    "specifically when calling `pybm run`, or "
                    "use the -A/--all switch."
                )

        if run_all:
            env_ids = [env.name for env in env_store.environments]

        # in order to revert to original checkout after benchmarks
        root_checkout = env_store.get("root").worktree.get_ref_and_type()

        for env_id in env_ids:
            if checkout_mode:
                # check out given reference
                environment = env_store.switch(name="root", ref=env_id)
            else:
                environment = env_store.get(env_id)

            worktree = environment.worktree
            subdir = create_subdir(result_dir=result_dir, worktree=worktree)

            runner.check_required_packages(environment=environment)

            with discover_targets(
                worktree=worktree, source_path=source_path, source_ref=source_ref
            ) as benchmark_targets:
                n = len(benchmark_targets)
                if n > 0:
                    print(
                        f"Found a total of {n} benchmark targets for "
                        f"environment {environment.name!r}."
                    )
                else:
                    msg = (
                        f"Benchmark selector {source_path!r} did not "
                        f"match any directory or Python files in "
                        f"environment {environment.name!r}."
                    )

                    if runner.fail_fast:
                        error_msg = (
                            "Aborted benchmark run because fast "
                            "failure mode was enabled."
                        )
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
                        benchmark_context=options.benchmark_context,
                    )

                    if rc != 0:
                        raise PybmError(
                            "Something went wrong during the "
                            "benchmark. stderr output of the "
                            f"dispatched subprocess:\n{data}"
                        )
                    else:
                        # TODO: Switch this to a general IO Connector later
                        result_name = Path(benchmark).stem + "_results.json"
                        result_file = subdir / result_name
                        with open(result_file, "w") as res:
                            json.dump(json.loads(data), res)

        if checkout_mode:
            root_ref, root_type = root_checkout
            print(f"Reverting checkout to {root_type} {root_ref!r}.")
            env_store.switch(name="root", ref=root_ref)

        print("Finished benchmarking in all specified environments.")

        return SUCCESS
