from .base import BaseCommand
from .create import CreateCommand

command_db = {
    "base": BaseCommand(name=""),
    "create": CreateCommand(name="create")
}
