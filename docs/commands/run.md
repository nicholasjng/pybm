# The `run` command

```shell
➜ pybm run -h
usage: pybm run <benchmark> <environment(s)> [<options>]

    Run pybm benchmark workloads in specified environments.

positional arguments:
  <benchmark>           Name of the benchmark target(s) to run. Can be a path to a single file, a directory, or a glob expression. Given paths need to be relative to the worktree root.
  <environment(s)>      Environments to run the benchmarks in. If omitted, by default, benchmarks will be run in the main environment if only one environment exists, otherwise an error will be raised,
                        unless the "--all" switch is used.

optional arguments:
  -h, --help            Show this message and exit.
  -v                    Enable verbose mode. Makes pybm log information that might be useful for debugging.
  -m                    Run benchmark targets as modules. Use this to benchmark code outside of a package.
  --checkout            Run benchmarks in checkout mode in environment "root". Here, instead of persisted git worktrees, different refs are benchmarked using `git checkout` commands.
  --all                 Run specified benchmarks in all existing pybm environments.
  -S <git-ref>, --source <git-ref>
                        Source benchmark targets from a different git reference.
  --repetitions <reps>  Number of repetitions for the target benchmarks.
  --filter <regex>      Regular expression to selectively filter benchmarks by name in the target files.
  --context <context>   Additional global context, given as strings in the format--context='key'='value'. Keys must be unique, supplying two or more context values for the same key results in an error.
```

The `pybm run` command is perhaps the heart of `pybm`'s functionality. It is responsible for discovering, dispatching
and running the appropriate benchmarks across the chosen environments. There are multiple nuances to running benchmarks
in pybm, all of which will be covered now.

## Understanding the basics

If you have your benchmarks under a `benchmarks` folder in your project, run all benchmarks like this, supposing you
want to run them sequentially in environments named `my-env1` to `my-envN`:

```shell
pybm run benchmarks my-env1 my-env2 ... my-envN
```

This will run the benchmarks in all the environments from my-env1 to my-envN.

Running a single file (let it be `foo.py`) inside a folder also works:

```shell
pybm run benchmarks/foo.py my-env1 my-env2 ... my-envN
```

Lastly, you can also supply a glob expression:

```shell
# runs all benchmark files starting with foo.
pybm run benchmarks/foo*.py my-env1 my-env2 ... my-envN
```

## Running benchmarks in all available environments

To run a benchmark in *all* available environments (list them with `pybm env list`), use the `--all` switch:

```shell
# runs all files in the benchmarks folder in all environments.
pybm run benchmarks --all
```

## Running benchmarks in module mode

Suppose you have a Python package that is not installed in your current virtual environment. As such, module name
resolution will likely fail due to the module not residing in Python's module path.

A solution is to write some package metadata (a `setup.py` or `setup.cfg/pyproject.toml` file) and install the package
from source. If you do not want to do that, however, or want to benchmark your code dynamically (e.g. while developing),
you can choose to run your Python file as a module:

```shell
python /path/to/file.py -> python -m path.to.file
```

Instead of the slashes in the file path, you substitute those with dots to reflect module structure.

pybm supports running benchmark target files as modules like this:

```shell
# runs the foo benchmark file as a module in the environment named my-env.
pybm -m benchmarks/foo.py my-env
```

Under the hood, this results in a `python -m benchmarks.foo` call, where the Python executable is sourced from the
benchmark environment's associated virtual environment.

## Running benchmarks in checkout mode

For some use cases, creating different benchmark environments is overkill because there is no need for custom package
dependencies, different Python versions etc. In this case, different versions of your Python codebase can be benchmarked
with simple `git checkout` commands.

If you do not have any need for custom environments, then you can use the `--checkout` flag to run benchmarks in
checkout mode:

```shell
pybm run benchmarks ref1 ref2 ... refN --checkout
```

This will check out different versions of your Python source code given by `ref1` to `refN`. Each of these can be any
valid git reference (branch name, tag name, (partial) commit SHA). In the end, the checkout is reverted to the ref that
was checked out before the call to `pybm run`.

Usually, as a rule of thumb, checkout mode can be used if:

* You do not have any changing dependencies between benchmarks,
* Your project does not have any C extensions / libraries that need to be (re)compiled,
* You want to use the same Python version for each of the benchmark runs.

If you do happen to meet any of the above criteria, consider using dedicated benchmark environments.

## Sourcing benchmarks from different references in checkout mode

Suppose you want to benchmark different git references in a project, but either:

* The benchmark suite you want to run is not present in some (or all) of the references.
* The benchmark suite you want to run is not constant between all references, i.e. file changes happened between
  different refs.

To obtain sensible comparisons between different git references, the benchmark suite should be the same, or otherwise
comparable between refs. One way to accomplish this is the `-S/--source` switch of `pybm run`:

```shell
# sources the benchmarks from the project's "main" branch.
pybm run benchmarks ref1 ref2 ... refN -S main --checkout
```

This command tells pybm to source the benchmark suite from the project's `main` branch, creating the same frame of
reference between all branches (namely that of the current HEAD of `main`.) After the benchmark is complete, the
sourcing is reversed by restoring the state of the current ref in git (before the benchmark sourcing).

⚠️ This command might not work out of the box if the source branch contains code that does not exist in one of the
target references; in that case, errors can occur due to undefined functions sourced into the benchmarked refs.

## Filtering benchmarks from target source files

You already know that you can run single-source-file benchmarks by supplying a file name to `pybm run`, or a set of
source files matching a glob expression. The same holds true for benchmark targets _inside_ a source file.

Suppose your benchmark file looks like this:

```python
# my_benchmark.py

def f():
    ...


def g():
    ...


def f2():
    ...


def h():
    ...
```

To run all benchmark functions with a name similar to `f`, you can supply a regex filter matching benchmark targets in
the source file(s).

```shell
# runs all targets containing the letter "f"
pybm run benchmarks/my_benchmark.py --filter="f"
```

## Adding context to benchmark runs

Sometimes, it is important to add contextual information to a benchmark. What kind of hardware did the code run on? What
is the cache size? What option was used for a certain API call?

To embed this type of information into benchmark results, `pybm` has a mechanism called **context**. This was adapted
from the [Google Benchmark](https://github.com/google/benchmark/) project, which has a similar functionality.

In short, a piece of context is a key-value pair giving some information about a part of the benchmark process. There
are two ways of specifying context in a benchmark run, each referring to a different kind of context:

1) **Global context**. This type of information is constant across the whole benchmark run. An example would be
   architectural information such as clock speeds, cache sizes, number of cores.
2) **Local context**. This information can vary between benchmark _targets_, i.e. different functions being benchmarked.

Global context can be specified at the CLI level with the `--context` switch of `pybm run`.

```shell
# get the number of cores from some fictitious shell function "getnumcores"
pybm run benchmarks root --context=pwd=$(pwd) --context=numcores=$(getnumcores)
```

Then, in the benchmark results, the current directory and number of cores will appear under the corresponding keys:

```json
// result.json
{
  "context": {
    ...
    "pwd": "/path/to/project",
    "numcores": 4,  // suppose it was run on a quad-core machine
    ...
  }
}
```

