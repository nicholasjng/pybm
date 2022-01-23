from .base import BaseCommand
from .compare import CompareCommand
from .config import ConfigCommand
from .env import EnvCommand
from .init import InitCommand
from .run import RunCommand

command_db = {
    "base": BaseCommand,
    "compare": CompareCommand,
    "config": ConfigCommand,
    "env": EnvCommand,
    "init": InitCommand,
    "run": RunCommand,
}
