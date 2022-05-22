# The `delete` command

```
pybm delete <identifier> [<options>]

positional arguments:
  <id>         Information that uniquely identifies the workspace. Can be name, checked out commit/branch/tag name, or worktree root directory.

optional arguments:
  -h, --help   Show this message and exit.
  -v           Enable verbose mode. Makes pybm log information that might be useful for debugging.
  -f, --force  Force worktree removal, including untracked files and changes.
```

Use the `pybm delete` command to delete a benchmark workspace. The identifier can be the git reference name (
partial SHAs also work), a benchmark workspace name or a directory name.

In the (standard) case of a virtual environment being created directly inside the git worktree, this virtual environment
will be removed upon deletion of the benchmark workspace; this behavior cannot be changed as git physically removes
the associated worktree. If you want to reuse a Python virtual environment, consider linking it explicitly from another
location with the `-L` switch in the `pybm workspace create` command - pybm will not remove these.

⚠️ As the main git worktree cannot be removed, the `main` pybm workspace cannot be deleted via `pybm delete`.