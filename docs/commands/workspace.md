# The `workspace` command

```shell
➜ pybm workspace -h
usage: pybm workspace install <name> <packages> [<options>]
   or: pybm workspace link <name> <path>
   or: pybm workspace list
   or: pybm workspace sync [<options>]
   or: pybm workspace uninstall <name> <packages> [<options>]

    Inspect, list, and manage pybm benchmark workspaces.


optional arguments:
  -h, --help  Show this message and exit.
  -v          Enable verbose mode. Makes pybm log information that might be useful for debugging.
```

The `pybm workspace` command is used for benchmark workspace lifecycle management. Benchmark workspaces are an abstraction
to test Python code under different simulated conditions that cannot be replicated with simple git checkouts. This
includes running your code with different Python versions (e.g. 3.9 vs. 3.7) or installing different versions of package
dependencies.

A benchmark workspace consists of a git worktree (a physical checkout of a git reference on disk) and an associated
Python virtual environment. Virtual workspaces are the de facto standard solution for setting up siloed Python
installations to avoid cluttering the system Python; for more information, please refer to the Python docs on virtual
workspaces.

## pybm workspace install

```
pybm workspace install <identifier> <packages> [<options>]

positional arguments:
  <id>                  Information that uniquely identifies the workspace. Can be name, checked out commit/branch/tag name, or worktree root directory.
  <packages>            Package dependencies to install into the new virtual environment.

optional arguments:
  -h, --help            Show this message and exit.
  -v                    Enable verbose mode. Makes pybm log information that might be useful for debugging.
  
Additional options from configured workspace builder 'pybm.builders.VenvProvider':
  -r <requirements>     Requirements file for dependency installation in the newly created virtual environment.
  --pip-options [<options> ...]
                        Space-separated list of command line options for dependency installation in the createdvirtual environment using `pip install`. To get a comprehensive list of options, run `python
                        -m pip install -h`.
```

This command installs new Python packages into a benchmark workspace's associated virtual environment.

⚠️ This command is largely dependent on the configured `Provider` class, which is used to manage Python virtual
workspaces; for different builder implementations, this command can have different command line arguments. The
default `VenvProvider` uses the Python standard library's `venv` to create virtual environments, and the `pip` package
manager to install/uninstall packages.

## pybm workspace uninstall

```
pybm workspace uninstall <identifier> <packages> [<options>]

positional arguments:
  <id>                  Information that uniquely identifies the workspace. Can be name, checked out commit/branch/tag name, or worktree root directory.

optional arguments:
  -h, --help            Show this message and exit.
  -v                    Enable verbose mode. Makes pybm log information that might be useful for debugging.
```

This command uninstalls existing Python packages from a benchmark workspace's associated virtual environment.

⚠️ This command is largely dependent on the configured `Provider` class, which is used to manage Python virtual
workspaces; for different builder implementations, this command can have different command line arguments. The
default `VenvProvider` uses the Python standard library's `venv` to create virtual environments, and the `pip` package
manager to install or uninstall packages.

## pybm workspace list

```
pybm workspace list

optional arguments:
  -h, --help  Show this message and exit.
  -v          Enable verbose mode. Makes pybm log information that might be useful for debugging.
```

This command lists all currently available benchmark workspaces in a table in the console. An example output could
look like this:

```
➜ pybm workspace list
 Name | Git Reference  | Reference type | Worktree directory       | Python version
------+----------------+----------------+--------------------------+----------------
 main | master         | branch         | ~/Workspaces/python/pybm | 3.9.9         
```

## pybm workspace update

This functionality is not yet implemented. It will be added in coming versions.