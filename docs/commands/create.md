# The `create` command

```
pybm create <commit-ish> <name> <dest> [<options>]

positional arguments:
  <commit-ish>          Commit, branch or tag to create a git worktree for.
  <name>                Unique name for the created workspace. Can be used to reference workspaces from the command line.
  <dest>                Destination directory of the new worktree. Defaults to repository-name@{commit|branch|tag}.

optional arguments:
  -h, --help            Show this message and exit.
  -v                    Enable verbose mode. Makes pybm log information that might be useful for debugging.
  -f, --force           Force worktree creation. Useful for checking out a branch multiple times with different custom requirements.
  -R, --resolve-commits
                        Always resolve the given git ref to its associated commit. If the given ref is a branch name, this detaches the HEAD (see https://git-scm.com/docs/git-checkout#_detached_head).
  --no-checkout         Skip worktree checkout after creation. Useful for sparsely checking out branches.
  -L <path-to-venv>, --link-existing <path-to-venv>
                        Link an existing Python virtual environment to the created pybm workspace. Raises an error if the path does not exist or is not recognized as a valid Python virtual environment.
```

Use `pybm create` to create a new benchmark workspace for a specified git reference:

```shell
pybm create my-branch my-workspace
```

This operation creates a benchmark workspace for a git branch named my-branch, and gives it the name my-workspace. This
given name can be used in pybm to reference a workspace, so it is useful to give expressive names to workspaces.

By default, the benchmark workspace with the repository root worktree is given the name `main`; if you choose not to
specify a name, pybm defaults to the `workspace_i` naming scheme, where `i` is an index starting at 1.

Further positional and optional arguments are:

The `-L` option can be used to link an existing virtual environment to a benchmark workspace. Suppose you have a
ready workspace at `/path/to/venv`; then `pybm workspace create my-branch -L /path/to/venv` will link the existing virtual
environment into the benchmark workspace.

✅ Not only branch names work as valid git references - you can also supply tag names or full/partial commit SHAs. In the
latter case, the SHA fragment is directly passed to git, which can fail to resolve a unique reference if the fragment is
too short. For a project with lots of commits, increasing the SHA fragment length can help avoid resolution errors.