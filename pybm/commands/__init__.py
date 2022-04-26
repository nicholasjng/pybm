from .compare import CompareCommand
from .config import ConfigCommand
from .create import CreateCommand
from .delete import DeleteCommand
from .init import InitCommand
from .run import RunCommand
from .switch import SwitchCommand
from .workspace import WorkspaceCommand

command_db = {
    "compare": CompareCommand,
    "config": ConfigCommand,
    "create": CreateCommand,
    "delete": DeleteCommand,
    "init": InitCommand,
    "run": RunCommand,
    "switch": SwitchCommand,
    "workspace": WorkspaceCommand,
}
