import os
import re

# environment variable regex modeled after the POSIX spec
# https://stackoverflow.com/questions/2821043/allowed-characters-in-linux-environment-variable-names/2821201#2821201
envvar_pattern = re.compile(r"\$([a-zA-Z_]+[a-zA-Z0-9_]*)")


def env_constructor(loader, node):
    """
    Custom node constructor substituting environment variable names for their values.

    If an environment variable is not found, the variable name is instead
    resubstituted back into the YAML node."""
    value = loader.construct_scalar(node)
    for group in envvar_pattern.findall(value):
        value = value.replace(f"${group}", os.getenv(group, f"${group}"))
    return value
