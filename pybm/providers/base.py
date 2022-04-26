from pathlib import Path
from typing import Optional, List, Union

from pybm.exceptions import ProviderError
from pybm.specs import PythonSpec
from pybm.workspace import Workspace


class BaseProvider:
    """Base class for all Python virtual environment providers."""

    def __init__(self, name="base"):
        self.ex_type = ProviderError
        self.name = name

    def add(
        self,
        workspace: Workspace,
        packages: List[str],
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> None:
        raise NotImplementedError

    def create(
        self,
        executable: Union[str, Path],
        destination: Union[str, Path],
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> PythonSpec:
        raise NotImplementedError

    def delete(self, spec: PythonSpec, verbose: bool = False) -> None:
        raise NotImplementedError

    def install(
        self,
        workspace: Workspace,
        extra_packages: Optional[List[str]] = None,
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> None:
        raise NotImplementedError

    def link(self, path: Union[str, Path], verbose: bool = False) -> PythonSpec:
        raise NotImplementedError

    def remove(
        self,
        workspace: Workspace,
        packages: List[str],
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ):
        raise NotImplementedError
