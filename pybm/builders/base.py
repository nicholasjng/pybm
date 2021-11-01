from pathlib import Path
from typing import Optional, List, Union

from pybm import PybmConfig
from pybm.exceptions import BuilderError
from pybm.specs import PythonSpec


class PythonEnvBuilder:
    """Base class for all Python virtual environment builders."""

    def __init__(self, config: PybmConfig):
        super().__init__()
        self.ex_type = BuilderError
        self.wheel_caches = []
        wheel_cache_string: str = config.get_value(
            "builder.localWheelCaches")
        if wheel_cache_string != "":
            self.wheel_caches = wheel_cache_string.split(":")

    def add_arguments(self, command: str):
        raise NotImplementedError

    def create(self,
               executable: Union[str, Path],
               destination: Union[str, Path],
               options: Optional[List[str]] = None,
               verbose: bool = False) -> PythonSpec:
        raise NotImplementedError

    def delete(self, env_dir: Union[str, Path], verbose: bool = False) -> None:
        raise NotImplementedError

    def link(self, env_dir: Union[str, Path], verbose: bool = False) \
            -> PythonSpec:
        raise NotImplementedError

    def install_packages(self,
                         spec: PythonSpec,
                         packages: Optional[List[str]] = None,
                         requirements_file: Optional[str] = None,
                         options: Optional[List[str]] = None,
                         verbose: bool = False) -> None:
        raise NotImplementedError

    def uninstall_packages(self,
                           spec: PythonSpec,
                           packages: List[str],
                           options: Optional[List[str]] = None,
                           verbose: bool = False) -> None:
        raise NotImplementedError

    def list_packages(self, executable: Union[str, Path],
                      verbose: bool = False):
        raise NotImplementedError
