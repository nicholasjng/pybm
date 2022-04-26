from pathlib import Path
from typing import List, Optional, Union

from pybm.providers import BaseProvider
from pybm.specs import PythonSpec
from pybm.workspace import Workspace


class PythonPoetryProvider(BaseProvider):
    def add(
        self,
        workspace: Workspace,
        packages: List[str],
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> None:
        pass

    def create(
        self,
        executable: Union[str, Path],
        destination: Union[str, Path],
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> PythonSpec:
        pass

    def delete(self, spec: PythonSpec, verbose: bool = False) -> None:
        pass

    def install(
        self,
        workspace: Workspace,
        extra_packages: Optional[List[str]] = None,
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> None:
        pass

    def link(self, path: Union[str, Path], verbose: bool = False) -> PythonSpec:
        pass

    def remove(
        self,
        workspace: Workspace,
        packages: List[str],
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ):
        pass
