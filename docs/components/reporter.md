# The reporter component

The `BenchmarkReporter` class component of `pybm` is responsible for reporting and interpreting the results of
previously run benchmarks. It works by running a (small-scale) data processing pipeline on the saved JSON files
containing the benchmark results.

An abstract base class interface is the `pybm.reporters.BaseReporter`.

## Loading benchmark result files

The first step of our result display pipeline is the loading step, handled by the `reporter.load()` API:

```python
def load(
        self, ref: str, result: Union[str, Path], target_filter: Optional[str] = None
):
    raise NotImplementedError
```

The `ref` argument describes for which git reference the results should be loaded. The `result` variable is a path-like
object, holding the path to a benchmark run's result directory. The optional `target_filter` argument can be used to
filter benchmark results inside the result folder via regex (within `pybm`, results are usually saved under the same
file name as their originating benchmark files, with a .json extension).

## Implementing `report` mode

For simple result reporting, without any relative differences / comparisons, the `reporter.report` API can be used:

```python
def report(
        self,
        ref: str,
        result: Union[str, Path],
        target_filter: Optional[str] = None,
        benchmark_filter: Optional[str] = None,
        context_filter: Optional[str] = None,
) -> None:
    raise NotImplementedError
```

The `ref`, `result`, and `target_filter` arguments are passed to the `runner.load()` API, while `benchmark_filter`
and `context_filter` are similar regex filters, which can be used to filter benchmark names and context values,
respectively.

⚠️ This API is subject to change, since `report` and `compare` mode are very similar in nature. Subsequent versions
of `pybm` can be expected to unify both functionalities under a single API (and CLI command).

## Implementing `compare` mode

For comparative reporting, comparing results across different git references, the `reporter.compare` API can be used:

```python
def compare(
    self,
    *refs: str,
    result: Union[str, Path],
    target_filter: Optional[str] = None,
    benchmark_filter: Optional[str] = None,
    context_filter: Optional[str] = None
) -> None:
    raise NotImplementedError
```

In this case, multiple `ref` objects can be passed as positional arguments. All other arguments work exactly as before.