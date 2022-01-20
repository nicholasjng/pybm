The `report` command

```shell
➜ pybm report -h
usage: pybm report <run> <ref> [<options>]

    Report benchmark results from specified sources.
    

positional arguments:
  <run>                 Benchmark run to report results for. To report the preceding run, use the "latest" keyword. To report results of the n-th preceding run (i.e., n runs ago), use the "latest^{n}"
                        syntax.
  <ref>                 Reference to display benchmark results for. Mandatory.

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

This command can be used to report results from a previous benchmark run. In contrast to `pybm compare`, the data is
presented in a vacuum, without comparison or relative difference to any other git reference.

## Reporting results for a reference

The calling convention for `pybm report` is as follows.

```shell
pybm report latest my-ref
```

⚠️ Currently, it is not possible to list anything other than the results of the previous run. More functionality will be
added in upcoming releases.

## Filtering data in `pybm report`

If you run a lot of benchmarks, but do not want to report all of them at the same time, it is useful to report only
subsets of information at one time. To this end, `pybm report` provides several options for filtering benchmark data,
all on the basis of regex matching.

### Filtering benchmark files

This option filters out benchmarks by their encompassing source file. Say you have two benchmark files, `foo.py`
and `bar.py`. To only list benchmark results from `foo.py`, you can do this:

```shell
# only compare results from foo.py.
pybm report latest my-ref --benchmark-filter="foo"
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
pybm report latest my-ref --target-filter="f"
```

### Filtering benchmark context

This option is useful for filtering out benchmark context in the reports. To learn more about benchmark context values,
read the docs about the [run command](run.md).

Filtering out context values works like this:

```shell
# filter out everything besides `myctx` context values.
pybm report latest my-ref --context-filter="myctx"
```

All the above filtering methods can be combined to selectively report only the data you want.