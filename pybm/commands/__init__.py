from .base import BaseCommand
from .config import ConfigCommand
from .env import EnvCommand
from .init import InitCommand
from .run import RunCommand

command_db = {
    "base": BaseCommand,
    "config": ConfigCommand,
    "env": EnvCommand,
    "init": InitCommand,
    "run": RunCommand,
}
