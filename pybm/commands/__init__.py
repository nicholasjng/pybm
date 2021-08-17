from .base import BaseCommand
from .create import CreateCommand
from .destroy import DestroyCommand

command_db = {
    "base": BaseCommand(name=""),
    "create": CreateCommand(name="create"),
    "destroy": DestroyCommand(name="destroy")
}
