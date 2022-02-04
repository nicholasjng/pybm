from pathlib import Path
from typing import Optional, List, Union

from pybm import PybmConfig
from pybm.exceptions import BuilderError
from pybm.specs import PythonSpec


class BaseBuilder:
    """Base class for all Python virtual environment builders."""

    def __init__(self, config: PybmConfig):
        super().__init__()
        self.ex_type = BuilderError
        self.wheel_caches = []

        wheel_cache_str: str = config.get_value("builder.wheelcaches")
        if wheel_cache_str != "":
            self.wheel_caches = wheel_cache_str.split(":")

    def additional_arguments(self, command: str):
        raise NotImplementedError

    def create(
        self,
        executable: Union[str, Path],
        destination: Union[str, Path],
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> PythonSpec:
        raise NotImplementedError

    def delete(self, env_dir: Union[str, Path], verbose: bool = False) -> None:
        raise NotImplementedError

    def install(
        self,
        spec: PythonSpec,
        packages: Optional[List[str]] = None,
        requirements_file: Optional[str] = None,
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> None:
        raise NotImplementedError

    def link(self, env_dir: Union[str, Path], verbose: bool = False) -> PythonSpec:
        raise NotImplementedError

    def list(self, executable: Union[str, Path], verbose: bool = False) -> List[str]:
        raise NotImplementedError

    def uninstall(
        self,
        spec: PythonSpec,
        packages: Optional[List[str]] = None,
        requirements_file: Optional[str] = None,
        options: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> None:
        raise NotImplementedError
