__all__ = ["CommandError", "GitError", "BuilderError", "PybmError"]


class CommandError(ValueError):
    pass


class GitError(ValueError):
    pass


class BuilderError(ValueError):
    pass


class PybmError(ValueError):
    pass
