# pybm: Repeatable Python benchmarking with git.

## What is pybm?

**pybm** is a Python CLI for reproducible benchmarking of Python code inside a git repository. It uses git's
version control features to track changes in performance between points of interest in git history. Out of many
possible use cases, three specific ones immediately emerge:

- Comparing performance of a feature branch (e.g. a pull request on GitHub) to the current development branch.
- Tracking changes in performance across the git history (e.g. releases, refactors).
- Adding a benchmarking step to a continuous integration (CI) workflow, and rejecting changes if they reduce
  performance to a significant degree.

## Notable features

The main concepts of pybm are:

- Creation and management of workspaces, consisting of a git reference (commit/branch/tag) and an associated
  Python virtual environment with the desired dependencies.
- Running benchmarks inside a workspace, with optional filtering, additional context information, and user-specific
  metrics tracking.
- Reporting results in direct comparison between workspaces to find and quantify performance changes.

## Installation

**pybm** is available via the standard Python package management tool `pip`:

```
python3 -m pip install git+https://github.com/nicholasjng/pybm
```

**NOTE**: There also exists a PyPI package called `pybm`, which is not affiliated with this project. Presently, the only
way to install pybm is through use of pip and git in the way above.

## Quickstart

Initialize `pybm` inside your Python git repository:

```shell
# Inside your project's main directory
pybm init
```

If you need to maintain different requirements between different git references, create a new workspace and install
your requirements:

```shell
pybm create my-ref my-workspace
```

Now, locate your benchmarks. To each of your benchmark files, simply add the following small execution block:

```python
# benchmark.py

import pybm


def my_benchmark_1():
    ...


def my_benchmark_2():
    ...


# more benchmarks ...

if __name__ == "__main__":
    pybm.run(module_context=globals())
```

This way, `pybm` can properly process the information and requirements for each benchmark environment individually.

There are two options to run your benchmarks:

1) With custom requirements and environments,

```shell
# folders or glob expressions also work for benchmark discovery.

# or use --all to run in all existing environments
pybm run benchmark.py my-workspace1 my-workspace2 [...] my-workspaceN
```

or

2) with the same Python virtual environment between all refs:

```shell
pybm run benchmark.py my-ref1 my-ref2 [...] my-refN --use-checkouts
```

If you did not install your Python package locally, consider running your benchmarks in module mode:

```shell
pybm run benchmark.py my-ref1 [...] my-refN --as-module --use-checkouts
```

## Requirements

The most central requirement to **pybm** is `git`, which is responsible for building benchmark workspaces. Currently,
at least `git version 2.17.0` (April 2018) is required for pybm to work correctly. To check your current git version,
run `git --version`, which should result in an output showing the version number, similar to the one above.

On the Python side, in its most standard configuration, **pybm** works almost entirely within the Python standard
library - only the `pyyaml` package is required for configuration management. Additional functionality is available via
extras installation:

```
# Google Benchmark Runner
python -m pip install git+https://github.com/nicholasjng/pybm[gbm]
```

More features are planned for following releases of this project. For current feature requests and implementation
status, check the Issues tab and the upcoming milestones.

## Documentation and examples

For some additional documentation on pybm commands, check the [docs](docs) section. For introductory examples in the
form of step-by-step walkthroughs, refer to the [examples](examples) section.

## Current status

**pybm** is currently still in an experimental phase. While most functionality has already been put to the test, you can
expect some sharp edges when using it for your own benchmarking purposes.

Functionality has so far been tested on macOS ARM64 (my development machine), Windows 10 (my secondary PC) and Ubuntu
through GitHub Actions. While great care was exercised to exclusively use cross-platform Python APIs and thus make pybm
as portable as possible, flawless execution on other platforms cannot be guaranteed.

## Contributing to pybm

This is a hobby / side project. Development goes on as my free time and motivation dictate. If you have a suggestion for
additional functionality, want to report a bug or would like to contribute features, please open a GitHub issue or a
pull request.

If you are using pybm and want to share your experience with it, or if you have general feedback, please feel free to
send me an e-mail to the address in my GitHub profile.
