The `compare` command

```shell
➜ pybm compare -h
usage: pybm compare <run> <anchor-ref> <compare-refs> [<options>]

    Report benchmark results from specified sources.
    

positional arguments:
  <run>                 Benchmark run to report results for. To report the preceding run, use the "latest" keyword. To report results of the n-th preceding run (i.e., n runs ago), use the "latest^{n}"
                        syntax.
  <refs>                Benchmarked refs to compare. The first given ref will be treated as the anchor ref, relative to which all differences are reported. An error is raised if any of the given refs are
                        not present in the run.

optional arguments:
  -h, --help            Show this message and exit.
  -v                    Enable verbose mode. Makes pybm log information that might be useful for debugging.

Additional options from configured reporter class 'pybm.reporters.console.JSONConsoleReporter':
  --target-filter <regex>
                        Regex filter to selectively report benchmark target files. If specified, only benchmark files matching the given filter will be included in the report.
  --benchmark-filter <regex>
                        Regex filter to selectively report benchmarks from the matched target files. If specified, only benchmarks matching the given filter will be included in the report.
  --context-filter <regex>
                        Regex filter for additional context to report from the benchmarks. If specified, only context values matching the given context filter will be included in the report.
```

The compare command is the most important post-benchmark command in `pybm`. It is used to quantify performance
differences and other quantifiable changes between the benchmarked references.

## Comparing different references

The calling convention for `pybm compare` is as follows.

```shell
pybm compare latest my-ref1 my-ref2 my-ref3
```

In this example, the `my-ref1` git reference is taken to be the _anchor_ reference, serving as the starting point for
all comparisons. For benchmarking library performances, this could for example be the current HEAD of the `main` branch.

Then, differences in performance are calculated _relatively to the anchor ref_. For example, say you find a runtime of 2
seconds on `main`, which is your anchor ref, and 1 second on your compare branch, `my-ref1`. Then, the (signed) relative
performance difference will be -50%, as the code takes only half the time on the compared branch. If the roles are
reversed and the compared branch takes 2 seconds instead, the relative performance difference will be +100%.

⚠️ Currently, it is not possible to list anything other than the results of the previous run. More functionality will be
added in upcoming releases.

## Filtering data in `pybm compare`

If you run a lot of benchmarks, but do not want to compare all of them at the same time, it is useful to report only
subsets of information at one time. To this end, `pybm compare` provides several options for filtering benchmark data,
all on the basis of regex matching.

### Filtering benchmark files

This option filters out benchmarks by their encompassing source file. Say you have two benchmark files, `foo.py`
and `bar.py`. To only list benchmark results from `foo.py`, you can do this:

```shell
# only compare results from foo.py.
pybm compare latest my-ref1 my-ref2 ... --benchmark-filter="foo"
```

### Filtering benchmark targets

Here, you filter from all files, but only benchmark targets matching the given regex. Suppose you have a setup like
this:

```python
# foo.py

def f():
    ...


def f2():
    ...


def g():
    ...


def h():
    ...
```

To only report results from the `f`-like functions, you can use the following command:

```shell
pybm compare latest my-ref1 my-ref2 ... --target-filter="f"
```

### Filtering benchmark context

This option is useful for filtering out benchmark context in the reports. To learn more about benchmark context values,
read the docs about the [run command](run.md).

Filtering out context values works like this:

```shell
# filter out everything besides `myctx` context values.
pybm compare latest my-ref1 my-ref2 ... --context-filter="myctx"
```

All the above filtering methods can be combined to selectively report only the data you want.