# The `env` command

```shell
➜ pybm env -h
usage: pybm env create <commit-ish> <name> <dest> [<options>]
   or: pybm env delete <identifier> [<options>]
   or: pybm env install <packages> [<options>]
   or: pybm env uninstall <packages> [<options>]
   or: pybm env list
   or: pybm env update <env> <attr> <value>

    Create and manage pybm benchmark environments.
    

optional arguments:
  -h, --help  Show this message and exit.
  -v          Enable verbose mode. Makes pybm log information that might be useful for debugging.
```

The `pybm env` command is used for benchmark environment lifecycle management. Benchmark environments are an abstraction
to test Python code under different simulated conditions that cannot be replicated with simple git checkouts. This
includes running your code with different Python versions (e.g. 3.9 vs. 3.7) or installing different versions of package
dependencies.

A benchmark environment consists of a git worktree (a physical checkout of a git reference on disk) and an associated
Python virtual environment. Virtual environments are the de facto standard solution for setting up siloed Python
installations to avoid cluttering the system Python; for more information, please refer to the Python docs on virtual
environments.

## pybm env create

```
pybm env create <commit-ish> <name> <dest> [<options>]

positional arguments:
  <commit-ish>          Commit, branch or tag to create a git worktree for.
  <name>                Unique name for the created environment. Can be used to reference environments from the command line.
  <dest>                Destination directory of the new worktree. Defaults to repository-name@{commit|branch|tag}.

optional arguments:
  -h, --help            Show this message and exit.
  -v                    Enable verbose mode. Makes pybm log information that might be useful for debugging.
  -f, --force           Force worktree creation. Useful for checking out a branch multiple times with different custom requirements.
  -R, --resolve-commits
                        Always resolve the given git ref to its associated commit. If the given ref is a branch name, this detaches the HEAD (see https://git-scm.com/docs/git-checkout#_detached_head).
  --no-checkout         Skip worktree checkout after creation. Useful for sparsely checking out branches.
  -L <path-to-venv>, --link-existing <path-to-venv>
                        Link an existing Python virtual environment to the created pybm environment. Raises an error if the path does not exist or is not recognized as a valid Python virtual environment.
```

Use `pybm env create` to create a new benchmark environment for a specified git reference:

```shell
pybm env create my-branch my-env
```

This operation creates a benchmark environment for a git branch named my-branch, and gives it the name my-env. This
given name can be reused in pybm to reference different environments, so it is useful to give expressive names for
environments.

By default, the benchmark environment with the repository root worktree is given the name `root`; if you choose to not
specify a name, pybm defaults to the `env_i` naming scheme, where `i` is an index starting at 1.

Further positional and optional arguments are:

The last `-L` option can be used to link an existing virtual environment to a benchmark environment. Suppose you have a
ready environment at `/path/to/venv`; then `pybm env create my-branch -L /path/to/venv` will link the existing virtual
environment into the benchmark environment.

✅ Not only branch names work as valid git references - you can also supply tag names or full/partial commit SHAs. In the
latter case, the SHA fragment is directly passed to git, which can fail to resolve a unique reference if the fragment is
too short. For a project with lots of commits, increasing the SHA fragment length can help avoid resolution errors.

## pybm env delete

```
pybm env delete <identifier> [<options>]

positional arguments:
  <id>         Information that uniquely identifies the environment. Can be name, checked out commit/branch/tag name, or worktree root directory.

optional arguments:
  -h, --help   Show this message and exit.
  -v           Enable verbose mode. Makes pybm log information that might be useful for debugging.
  -f, --force  Force worktree removal, including untracked files and changes.
```

Use the `pybm env delete` command to delete a benchmark environment. The identifier can be the git reference name (
partial SHAs also work), a benchmark environment name or a directory name.

In the (standard) case of a virtual environment being created directly inside the git worktree, this virtual environment
will be removed upon deletion of the benchmark environment; this behavior cannot be changed as git physically removes
the associated worktree. If you want to reuse a Python virtual environment, consider linking it explicitly from another
location with the `-L` switch in the `pybm env create` command - pybm will not remove these.

## pybm env install

```
pybm env install <identifier> <packages> [<options>]

positional arguments:
  <id>                  Information that uniquely identifies the environment. Can be name, checked out commit/branch/tag name, or worktree root directory.
  <packages>            Package dependencies to install into the new virtual environment.

optional arguments:
  -h, --help            Show this message and exit.
  -v                    Enable verbose mode. Makes pybm log information that might be useful for debugging.
  
Additional options from configured environment builder 'pybm.builders.VenvBuilder':
  -r <requirements>     Requirements file for dependency installation in the newly created virtual environment.
  --pip-options [<options> ...]
                        Space-separated list of command line options for dependency installation in the createdvirtual environment using `pip install`. To get a comprehensive list of options, run `python
                        -m pip install -h`.
```

This command installs new Python packages into a benchmark environment's associated virtual environment.

⚠️ This command is largely dependent on the configured `Builder` class, which is used to manage Python virtual
environments; for different builder implementations, this command can have different command line arguments. The
default `VenvBuilder` uses the Python standard library's `venv` to create virtual environments, and the `pip` package
manager to install/uninstall packages.

## pybm env uninstall

```
pybm env uninstall <identifier> <packages> [<options>]

positional arguments:
  <id>                  Information that uniquely identifies the environment. Can be name, checked out commit/branch/tag name, or worktree root directory.

optional arguments:
  -h, --help            Show this message and exit.
  -v                    Enable verbose mode. Makes pybm log information that might be useful for debugging.

Additional options from configured environment builder 'pybm.builders.stdlib.VenvBuilder':
  <packages>            Package dependencies to uninstall from the benchmarking environment using pip.
  --pip-options [<options> ...]
                        Space-separated list of command line options for dependency removal in the benchmark environment using `pip uninstall`. To get a comprehensive list of options, run `python -m pip
                        uninstall -h`.
```

This command uninstalls existing Python packages from a benchmark environment's associated virtual environment.

⚠️ This command is largely dependent on the configured `Builder` class, which is used to manage Python virtual
environments; for different builder implementations, this command can have different command line arguments. The
default `VenvBuilder` uses the Python standard library's `venv` to create virtual environments, and the `pip` package
manager to install/uninstall packages.

## pybm env list

```
pybm env list

optional arguments:
  -h, --help  Show this message and exit.
  -v          Enable verbose mode. Makes pybm log information that might be useful for debugging.
```

This command lists all currently available benchmark environments in a table in the console. An example output could
look like this:

```
➜ pybm env list
 Name | Git Reference  | Reference type | Worktree directory       | Python version
------+----------------+----------------+--------------------------+----------------
 root | master         | branch         | ~/Workspaces/python/pybm | 3.9.9         
```

## pybm env update

This functionality is not yet implemented. It will be added in coming versions.