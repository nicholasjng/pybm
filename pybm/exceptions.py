__all__ = ["CommandError", "GitError", "ProviderError", "PybmError"]


class CommandError(ValueError):
    pass


class GitError(ValueError):
    pass


class ProviderError(ValueError):
    pass


class PybmError(ValueError):
    pass
