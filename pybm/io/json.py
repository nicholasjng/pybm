import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pybm import PybmError
from pybm.io.util import create_subdir, get_rundir
from pybm.util.common import dfilter_regex, lfilter, lfilter_regex, lmap
from pybm.util.path import get_subdirs, lsdir, is_empty

# these context values are protected and will always be present
PRIVILEGED_CONTEXT = ["executable", "ref", "commit"]


def _check_subdirs(result: Union[str, Path], refs: Tuple[str, ...]):
    subdirs = get_subdirs(result, absolute=False)

    for ref in refs:
        if ref not in subdirs:
            raise PybmError(f"No results exist for ref {ref!r}.")


class JSONFileIO:
    def __init__(self, result_dir: Union[str, Path]):
        self.rundir = get_rundir(result_dir)
        self.result_dir = result_dir

    def read(
        self,
        *refs,
        result: Union[str, Path],
        target_filter: Optional[str] = None,
        benchmark_filter: Optional[str] = None,
        context_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        path = self.result_dir / Path(result)

        if not path.exists() or not path.is_dir():
            raise PybmError(f"Given path {path} does not exist or is not a directory.")

        _check_subdirs(path, refs)

        json_files = lsdir(path=path, file_suffix=".json", include_subdirs=True)

        if len(refs) > 1:
            json_files = [f for f in json_files if any(ref in f.parts for ref in refs)]

        if target_filter is not None:
            json_files = lfilter_regex(
                target_filter, lmap(str, json_files)
            )  # type: ignore

        results = []

        for result_file in json_files:
            with open(result_file, "r") as file:
                benchmark_obj = json.load(file)
            # TODO: More extensive schema validation
            keys = ["context", "benchmarks"]

            if not all(key in benchmark_obj for key in keys):
                raise PybmError(
                    f"Malformed JSON object. Result {benchmark_obj} missing "
                    f"at least one of the expected keys: {', '.join(keys)}."
                )

            benchmarks, context = benchmark_obj["benchmarks"], benchmark_obj["context"]

            processed_ctx = {k: context[k] for k in PRIVILEGED_CONTEXT}

            if context_filter is not None:
                # only display context values matching the filter regex
                filtered = dfilter_regex(context_filter, context)
                processed_ctx.update(filtered)

            if benchmark_filter is not None:
                pattern = re.compile(benchmark_filter)

                benchmarks = lfilter(
                    lambda bm: pattern.search(bm["name"]) is not None, benchmarks
                )

            for benchmark in benchmarks:
                benchmark.update(processed_ctx)

            results += benchmarks

        return results

    def write(self, ref: str, file: Union[str, Path], obj: str):
        # TODO: Clean up rundir after exception
        self.rundir.mkdir(parents=False, exist_ok=True)

        subdir = create_subdir(result_dir=self.rundir, ref=ref)
        result_name = Path(file).stem + "_results.json"
        result_file = subdir / result_name

        with open(result_file, "w") as res:
            try:
                json.dump(json.loads(obj), res)
            except json.JSONDecodeError:
                # remove the subdirectory again
                subdir.rmdir()
                # remove rundir as well if it is empty
                if is_empty(self.rundir):
                    self.rundir.rmdir()

                raise PybmError(
                    f"Could not write benchmark results to file {result_file}: "
                    f"Unparseable JSON object {obj!r}."
                )
