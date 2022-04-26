# flake8: noqa: F401
from .base import BaseProvider
from .stdlib import PythonVenvProvider
from .poetry import PythonPoetryProvider

builders = {
    "venv": PythonVenvProvider,
    "poetry": PythonPoetryProvider,
}
