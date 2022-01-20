# The runner component

The `BenchmarkRunner` class component of `pybm` is responsible for running the benchmarks, parsing flags and writing
results to a specified location. The main functions are benchmark running, and optionally, dispatch as well as flag
creation / parsing.

An abstract base class interface is the `pybm.runners.BaseRunner`.

## The benchmark dispatch

`pybm` uses siloed off environments to run benchmarks in multiple pre-configured scenarios. As such, when running the
benchmarks, one has to call onto the correct Python executable as well. This is the `runner.dispatch()` method's
responsibility.

```python
def dispatch(
        self,
        benchmark: str,
        environment: BenchmarkEnvironment,
        run_as_module: bool = False,
        repetitions: int = 1,
        benchmark_filter: Optional[str] = None,
        benchmark_context: Optional[List[str]] = None,
        **runner_kwargs,
) -> Tuple[int, str]:
```

The arguments it takes are for the most part self-explanatory: `benchmark` is the path to the benchmark `.py` file,
`environment` is the target benchmark environment in which to run, `run_as_module` is a boolean indicating whether the
target is run as a script or as a Python module (see the [pybm run](../commands/run.md) docs for more info on this
option).

The arguments after that - repetitions, a target regex filter, context and runner-specific keyword arguments, are put
into a list with the `runner.create_flags()` API, and used as the `argv` argument to the Python runtime of the chosen
benchmark environment. At the end, `runner.dispatch()` spawns a `python` subprocess, where `python` is the
aforementioned environment-specific Python runtime.

## Running a benchmark

The main API for benchmark running that all benchmark runners have to implement is `runner.run_benchmarks()`.

Due to `pybm`'s implementation details, this method is not as straightforward.

```python
def run_benchmark(
        self, argv: Optional[List[str]] = None, module_context: Dict[str, Any] = None
) -> int:
    raise NotImplementedError
```

Its first argument, `argv`, is standard for a Python CLI entrypoint - this is exactly what its function is. The
`run_benchmarks` function receives a stringified list of arguments by another classmethod, `runner.dispatch` (featured
above). The `module_context` argument is a map-like object holding information on the Python module context in which the
function was called - this should almost always be `globals()`, an object holding the global variables available in the
current module.

Inside the logic of `run_benchmark`, these flags will have to be parsed out again to be available for use in the
benchmark logic - for this, the `runner.parse_flags` API is available.

⚠️ Be aware that you never call `runner.run_benchmark` directly - instead, inside your benchmark file, you insert this
block at the end:

```python
# benchmark.py

import pybm

(...)

if __name__ == "__main__":
    pybm.run(module_context=globals())
```
