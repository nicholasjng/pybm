from .base import BaseCommand
from .env import EnvCommand

command_db = {
    "base": BaseCommand(name=""),
    "env": EnvCommand(name="env"),
}
