import contextlib
import functools
import re
from pathlib import Path
from typing import List, Any, Dict, Union, Optional, Tuple

from pybm.exceptions import PybmError
from pybm.util.common import lfilter, dfilter, dkfilter, lmap
from pybm.util.functions import is_context_provider
from pybm.util.git import get_from_history
from pybm.util.imports import import_from_module
from pybm.util.path import lsdir
from pybm.util.formatting import abbrev_home
from pybm.workspace import Workspace


@contextlib.contextmanager
def discover_targets(
    workspace: Workspace,
    source_path: Union[str, Path],
    source_ref: Optional[str] = None,
    use_legacy_checkout: bool = False,
):
    root, name = workspace.root, workspace.name
    current_ref, ref_type = workspace.get_ref_and_type()

    # boolean flag indicating checkout
    checkout_complete = False

    print(
        f"Starting benchmark run for {ref_type} {current_ref!r} in workspace {name!r}."
    )

    try:
        if source_ref is not None and source_ref != current_ref:
            if workspace.has_untracked_files():
                raise PybmError(
                    "Sourcing benchmarks from other git reference requires a clean "
                    "worktree, but there are untracked files present in the worktree "
                    f"{abbrev_home(root)}. To fix this, either add untracked files to "
                    f"this worktree's staging area with `git add`, or remove the files "
                    f"with `git clean`."
                )

            print(
                f"Checking out benchmark resource {source_path} from git "
                f"reference {source_ref!r} into workspace {name!r}."
            )

            get_from_history(
                ref=source_ref,
                resource=source_path,
                directory=root,
                use_legacy_checkout=use_legacy_checkout,
            )

            checkout_complete = True

        print(
            f"Discovering benchmark targets for {ref_type} {current_ref!r} in "
            f"workspace {name!r}.....",
            end="",
        )

        benchmark_path = Path(root) / source_path

        if benchmark_path.is_dir():
            benchmark_targets = lmap(
                str, lsdir(benchmark_path, file_suffix=".py", relative_to=root)
            )
        elif benchmark_path.is_file():
            benchmark_targets = [str(source_path)]
        else:
            # assume it is a glob pattern
            ppath, glob = benchmark_path.parent, benchmark_path.name
            benchmark_targets = lmap(
                lambda p: str(p.relative_to(root)), ppath.glob(glob)
            )

        # filter out __init__.py files by default
        benchmark_targets = lfilter(
            lambda x: not x.endswith("__init__.py"), benchmark_targets
        )

        print("failed." if not benchmark_targets else "done.")

        yield benchmark_targets

    finally:
        if source_ref is not None and checkout_complete:
            # restore benchmark contents from original ref
            get_from_history(
                ref=current_ref,
                resource=source_path,
                directory=root,
                use_legacy_checkout=use_legacy_checkout,
            )

            # revert checkout of untracked files with `git clean`
            workspace.clean()

            print(
                f"Finished benchmark run for {ref_type} {current_ref!r} "
                f"in workspace {name!r} ."
            )


def filter_targets(module_context: Dict[str, Any], regex_filter: Optional[str] = None):
    # filter admissible targets as those from the __main__ module
    # of the subprocess (target .py file)
    is_main_member = functools.partial(is_module_member, module_name="__main__")

    filtered_context = dfilter(is_main_member, module_context)

    if regex_filter is not None:
        pattern = re.compile(regex_filter)
        filtered_context = dkfilter(
            lambda k: pattern.search(k) is not None, filtered_context
        )

    return filtered_context


def is_module_member(obj_tuple: Tuple[str, Any], module_name: str) -> bool:
    """Check membership of object in __main__ module to avoid benchmarking
    imports due to accidentally pattern matching them."""
    obj = obj_tuple[1]

    if not hasattr(obj, "__module__"):
        return False
    else:
        return obj.__module__ == module_name


def load_context_providers(provider_info: str) -> List[Any]:
    if provider_info != "":
        provider_names = provider_info.split(",")
    else:
        return []
    # require the context providers to come from an installed module
    imported = [import_from_module(name) for name in provider_names]
    return lfilter(is_context_provider, imported)


def validate_context(context: List[str], parsed: bool = False):
    """Validate a set of context information, either parsed (=with flag
    name and prefix chars stripped) or unparsed (the raw flags)."""
    expected_length: int = 2 if parsed else 3

    for ctx_val in context:
        seen: Dict[str, str] = {}
        split_ctx = ctx_val.split("=")
        if len(split_ctx) != expected_length:
            raise PybmError(
                f"Could not properly parse context value {ctx_val!r}. Context values "
                f"need to be given in the format --context='<key>=<value>'."
            )

        name, value = split_ctx[-2:]
        if name in seen:
            raise PybmError(
                f"Multiple values for context value {name!r} were given. Perhaps you "
                f"gave some context information twice, once on the command line as "
                f"global context, and via a set environment-specific context provider. "
                f"To check the currently set context providers, run the command "
                f"`pybm config get runner.contextproviders`."
            )
        else:
            seen[name] = value
