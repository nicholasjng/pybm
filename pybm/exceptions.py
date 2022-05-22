__all__ = ["CommandError", "GitError", "PybmError"]


class CommandError(ValueError):
    pass


class GitError(ValueError):
    pass


class PybmError(ValueError):
    pass
