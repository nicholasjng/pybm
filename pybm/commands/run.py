import warnings
from pathlib import Path
from typing import List, Optional

from pybm.command import CLICommand
from pybm.config import config, get_component
from pybm.exceptions import PybmError
from pybm.mixins.filemanager import WorkspaceManagerContextMixin
from pybm.reporters import BaseReporter
from pybm.runners import BaseRunner
from pybm.runners.util import discover_targets
from pybm.status_codes import SUCCESS, ERROR


class RunCommand(WorkspaceManagerContextMixin, CLICommand):
    """
    Run pybm benchmark workloads in specified workspaces.
    """

    usage = "pybm run <benchmarks> <workspace(s)> [<options>]\n"

    def __init__(self):
        super(RunCommand, self).__init__(name="run")

    def add_arguments(self):
        self.parser.add_argument(
            "benchmarks",
            type=str,
            help="Name of the benchmark target(s) to run. Can be a single Python "
            "file, a directory, or a glob expression. Given paths need to be relative "
            "to the workspace root.",
            metavar="<benchmark>",
        )
        self.parser.add_argument(
            "workspaces",
            nargs="*",
            default=None,
            help="Workspaces to run the benchmarks in. If omitted, by default, "
            "benchmarks will be run in the main workspace if only one workspace "
            "exists, otherwise an error will be raised, unless the '--all' switch is "
            "used.",
            metavar="<workspace(s)>",
        )
        self.parser.add_argument(
            "-m",
            action="store_true",
            default=False,
            dest="run_as_module",
            help="Run benchmark targets as modules. Use this to benchmark code outside "
            "of a package.",
        )
        self.parser.add_argument(
            "--checkout",
            action="store_true",
            default=False,
            help="Run benchmarks in checkout mode in workspace 'root'. Here, instead "
            "of persisted git worktrees, different refs are benchmarked using `git "
            "checkout` commands.",
        )
        self.parser.add_argument(
            "--all",
            action="store_true",
            default=False,
            dest="run_all",
            help="Run specified benchmarks in all existing pybm workspaces.",
        )
        self.parser.add_argument(
            "-S",
            "--source",
            type=str,
            default=None,
            dest="source_ref",
            metavar="<git-ref>",
            help="Source benchmark targets from git reference <git-ref> instead of "
            "the current ref.",
        )
        self.parser.add_argument(
            "--runner",
            type=str,
            default=None,
            choices=("timeit", "gbm"),
            metavar="<runner>",
            help="Runner class to use for running the benchmark workloads.",
        )
        self.parser.add_argument(
            "--repetitions",
            type=int,
            default=5,
            metavar="<N>",
            help="Number of times to repeat the target benchmarks.",
        )
        self.parser.add_argument(
            "--filter",
            type=str,
            default=None,
            dest="benchmark_filter",
            metavar="<regex>",
            help="Regular expression to selectively filter benchmarks by name in the "
            "target files.",
        )
        self.parser.add_argument(
            "--context",
            action="append",
            default=None,
            dest="benchmark_context",
            metavar="<context>",
            help="Additional global context, given as strings in the format "
            "--context='key'='value'. Keys must be unique, supplying more than one "
            "value for the same key results in an error.",
        )
        self.parser.add_argument(
            "--enable-random-interleaving",
            action="store_true",
            default=False,
            help="Enable random interleaving in Google Benchmark. This can reduce "
            "run-to-run variance by running benchmarks in random order.",
        )
        self.parser.add_argument(
            "--report-aggregates-only",
            action="store_true",
            default=False,
            help="Report only aggregates (mean/stddev) instead of the raw data in "
            "Google Benchmark. If you uncheck this option,  aggregates will still be "
            "reported if the number of benchmark repetitions is greater than 1.",
        )

    def run(self, args: List[str]) -> int:
        if not args:
            self.parser.print_help()
            return ERROR

        self.add_arguments()
        options = self.parser.parse_args(args)
        runner_options = vars(options)

        runner: BaseRunner = runner_options.pop("runner")

        if not runner:
            runner = get_component("runner")

        reporter: BaseReporter = get_component("reporter")

        # whether to use legacy checkouts (git < 2.17)
        use_legacy_checkout: bool = config.get_value("git.legacycheckout")

        verbose: bool = runner_options.pop("verbose")

        env_ids: List[str] = runner_options.pop("workspaces") or []
        run_all: bool = runner_options.pop("run_all")
        checkout_mode: bool = runner_options.pop("checkout")
        source_ref: Optional[str] = runner_options.pop("source_ref")
        source_path = Path(runner_options.pop("benchmarks"))
        run_as_module: bool = runner_options.pop("run_as_module")

        # runner dispatch arguments
        repetitions: int = runner_options.pop("repetitions")
        benchmark_filter: Optional[str] = runner_options.pop("benchmark_filter")
        benchmark_context = runner_options.pop("benchmark_context")
        # at this point, runner_options only include the additional runner kwargs

        if source_path.is_absolute():
            raise PybmError(
                f"Benchmark path {source_path!r} was given in absolute form. Please "
                f"specify the targets by a path relative to the workspace root."
            )

        if len(env_ids) > 0:
            if run_all:
                raise PybmError(
                    "The --all switch can only be used as a substitute for specific "
                    "workspace IDs, but the following workspaces were requested: "
                    f"{', '.join(env_ids)}. Please either omit the --all switch or "
                    f"the specific workspace IDs."
                )
        else:
            if checkout_mode:
                raise PybmError(
                    "When running in checkout mode, please specify at least one valid "
                    "git reference to benchmark. To benchmark the current checkout in "
                    f"the main workspace, run `pybm run {source_path} main`."
                )

            if not run_all and len(self.workspaces) > 1:
                raise PybmError(
                    "No workspaces were given as positional arguments to `pybm run`, "
                    "but more than one benchmark workspace exists in the current "
                    "repository. Please supply the desired target workspaces "
                    "explicitly when calling `pybm run`, or use the --all switch."
                )

        with self.main_context(verbose=verbose, readonly=True):
            if run_all:
                env_ids = list(self.workspaces.keys())

            # in order to revert to original checkout after benchmarks
            workspace = self.get("main", verbose=verbose)
            root_checkout = workspace.get_ref_and_type()

            for env_id in env_ids:
                if checkout_mode:
                    # check out given reference into main worktree
                    workspace.switch(ref=env_id)
                else:
                    workspace = self.get(env_id, verbose=verbose)

                ref, ref_type = workspace.get_ref_and_type()

                runner.check_required_packages(workspace=workspace)

                with discover_targets(
                    workspace=workspace,
                    source_path=source_path,
                    source_ref=source_ref,
                    use_legacy_checkout=use_legacy_checkout,
                ) as benchmark_targets:

                    n = len(benchmark_targets)
                    if n > 0:
                        print(
                            f"Found a total of {n} benchmark targets for {ref_type} "
                            f"{ref!r} in workspace {workspace.name!r}."
                        )
                    else:
                        msg = (
                            f"Benchmark selector {str(source_path)!r} did not match "
                            f"any directory or Python files for {ref_type} {ref!r} "
                            f"in workspace {workspace.name!r}."
                        )

                        if runner.fail_fast:
                            error_msg = (
                                "Aborted benchmark run because fast failure mode was "
                                "enabled."
                            )
                            raise PybmError("\n".join([msg, error_msg]))
                        else:
                            warnings.warn(msg)
                            continue

                    for i, benchmark in enumerate(benchmark_targets):
                        print(f"[{i + 1}/{n}] Running benchmark {benchmark}.....")

                        rc, data = runner.dispatch(
                            benchmark=benchmark,
                            workspace=workspace,
                            run_as_module=run_as_module,
                            repetitions=repetitions,
                            benchmark_filter=benchmark_filter,
                            benchmark_context=benchmark_context,
                            **runner_options,
                        )

                        if rc != 0:
                            raise PybmError(
                                "Something went wrong during the benchmark. "
                                f"Stderr output of the dispatched subprocess:\n{data}"
                            )

                        reporter.write(ref, benchmark, data)

            if checkout_mode:
                root_ref, root_type = root_checkout
                print(f"Reverting checkout to {root_type} {root_ref!r}.")
                workspace.switch(ref=root_ref, ref_type=root_type)

        print("Finished benchmarking in all specified workspaces.")

        return SUCCESS
