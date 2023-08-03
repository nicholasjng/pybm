__all__ = ["CommandError", "GitError", "PybmError", "PythonError"]


class CommandError(ValueError):
    pass


class GitError(ValueError):
    pass


class PybmError(ValueError):
    pass


class PythonError(ValueError):
    pass
