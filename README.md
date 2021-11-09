# pybm: Repeatable Python benchmarking with git.

## What is pybm?

**pybm** is a Python CLI for repeatable, declarative benchmarking of Python code
inside a git repository. It uses git's version control mechanisms to track
changes in performance between points of interest in git history. Out of many
possible use cases, three specific ones immediately emerge:

- Comparing performance of a feature branch to the current development branch.
- Tracking changes in performance across git history (e.g. releases, refactors).
- Adding a benchmarking step into a continuous integration (CI) pipeline, and
  rejecting changes if they reduce performance to a significant degree.

## Notable features

The main concepts of pybm are:

- Creation and management of benchmark environments, consisting of a git
  reference (commit/branch/tag) and an associated Python virtual environment
  containing the desired dependencies.
- Running benchmarks inside an environment, with optional filtering, additional
  context information, and user-specific metrics tracking.
- Reporting results in direct comparison between environments to find and
  quantify performance changes.

## Installation

**pybm** is available via the standard Python package management tool `pip`:

```
python -m pip install git+https://github.com/nicholasjng/pybm
```

**NOTE**: There also exists a PyPI package called `pybm`, which is not
affiliated with this project. Presently, the only way to install pybm is through
use of pip and git in the way above.

## Requirements

The most central requirement to **pybm** is `git`, a version control system,
which is responsible for building benchmark environments.
Currently, at least `git version 2.23.0` (August 2019) is required for pybm to
work correctly. To check your git version, run `git --version`, which
should result in an output showing the version number, similar to the one above.

On the Python side, in its most standard configuration, **pybm** works almost
entirely within the Python standard library - only the `pyyaml` package is
required for configuration management. Additional functionality is available via
extras installation:

```
# Google Benchmark Runner
python -m pip install git+https://github.com/nicholasjng/pybm[gbm]
```

More features are planned for following releases of this project. For current 
feature requests and implementation status, check the Issues tab and milestones.

## Documentation and examples

For some additional documentation on pybm commands, check the [docs](docs)
section. For introductory examples in the form of step-by-step walkthroughs,
check the [examples](examples) section.

## Current status

**pybm** is currently still in an experimental phase. While most functionality
has already been put to the test, you can expect some sharp edges when using it
for your own benchmarking purposes.

Functionality has so far been tested on Darwin ARM64 and macOS 11 (my
development machine), and Ubuntu through GitHub Actions. While great care was 
exercised to exclusively use cross-platform Python APIs and thus make pybm as 
portable as possible, flawless execution on other platforms cannot be 
guaranteed.

Windows will most likely not work out of the box (due to different command line 
calling conventions and executable names).

## Contributing to pybm

This is a hobby / side project. Development goes on as my free time and
motivation dictate. If you have a suggestion for additional functionality, want
to report a bug or would like to contribute features, please open a GitHub issue
or a pull request.

If you are using pybm and want to share your experience with it, or if you have
general feedback, please feel free to send me an e-mail under the address in my
GitHub profile.

## Origin

The idea for this project came in June 2021, during some hobby work on the JAX
project. Especially the custom Python requirements machinery became necessary
due to the different platforms and package requirements posed by JAX.
