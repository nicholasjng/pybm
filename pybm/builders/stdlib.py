"""
Virtual environment creation class for benchmarking
with custom requirements in Python."""
import shutil
from pathlib import Path
from typing import List, Optional, Union

from pybm.builders.base import PythonEnvBuilder
from pybm.config import PybmConfig
from pybm.exceptions import BuilderError
from pybm.specs import PythonSpec
from pybm.util.common import version_string


# TODO: Subclass directly from venv.EnvBuilder instead of going the
#  subprocess route
class VenvBuilder(PythonEnvBuilder):
    """Python standard library virtual environment builder class."""

    def __init__(self, config: PybmConfig):
        super().__init__(config=config)
        self.venv_home: str = config.get_value("builder.homeDirectory")

        # persistent venv options
        self.venv_options: List[str] = []
        venv_option_string: str = config.get_value(
            "builder.persistentVenvOptions")
        if venv_option_string != "":
            self.venv_options = venv_option_string.split(",")

        # persistent pip install options
        self.pip_install_options: List[str] = []
        pip_install_option_string: str = config.get_value(
            "builder.persistentPipInstallOptions")
        if pip_install_option_string != "":
            self.pip_install_options = pip_install_option_string.split(",")

        # persistent pip uninstall options
        self.pip_uninstall_options: List[str] = []
        pip_uninstall_option_string: str = config.get_value(
            "builder.persistentPipUninstallOptions")
        if pip_uninstall_option_string != "":
            self.pip_uninstall_options = \
                pip_uninstall_option_string.split(",")

    def create(self,
               executable: Union[str, Path],
               destination: Union[str, Path],
               options: Optional[List[str]] = None,
               verbose: bool = False) -> PythonSpec:
        options = options or []
        # create the venv in the worktree or in a special home directory
        if self.venv_home == "":
            env_dir = Path(destination) / "venv"
        else:
            env_dir = (Path(self.venv_home) / destination).resolve()

        # THIS LINE IS EXTREMELY IMPORTANT. Resolve symlinks if the
        # given Python interpreter was a symlink to begin with.
        resolved_executable = Path(executable).resolve()

        command = [str(resolved_executable), "-m", "venv", str(env_dir)]
        options += self.venv_options
        # Prevent duplicate options
        command += list(set(options))
        print(f"Creating virtual environment in directory {env_dir}.....",
              end="")
        self.run_subprocess(command)
        print("done.")

        executable = self.get_executable(env_dir)
        python_version = version_string(self.get_python_version(executable))
        return PythonSpec(root=str(env_dir),
                          executable=executable,
                          version=python_version,
                          packages=self.list_packages(executable))

    @staticmethod
    def delete(env_dir: Union[str, Path], verbose: bool = False) -> None:
        def onerror(ex_type, value, _):
            print("failed.")
            print(f"Attempt to remove virtual environment raised an exception "
                  f"of type {ex_type}:")
            print(str(value))

        if Path(env_dir).exists():
            print(f"Removing virtual environment at location {env_dir}.....",
                  end="")
            shutil.rmtree(env_dir, onerror=onerror)
            print("done.")

    def link_existing(self,
                      env_dir: Union[str, Path],
                      verbose: bool = False):
        print(f"Attempting to link existing virtual environment in location "
              f"{env_dir}.....")
        if (Path(self.venv_home) / env_dir).exists():
            path = Path(self.venv_home) / env_dir
        else:
            path = Path(env_dir)
        if not self.is_valid_venv(path, verbose=verbose):
            msg = f"The specified path {env_dir} was not recognized " \
                  f"as a valid virtual environment, since no `python`/" \
                  f"`pip` executables or symlinks were discovered."
            raise BuilderError(msg)
        executable = self.get_executable(env_dir)
        python_version = version_string(self.get_python_version(executable))
        packages = self.list_packages(executable, verbose=verbose)
        spec = PythonSpec(root=str(env_dir),
                          executable=executable,
                          version=python_version,
                          packages=packages)
        print(f"Successfully linked existing virtual environment in location "
              f"{env_dir}.")
        return spec

    def install_packages(self,
                         executable: str,
                         packages: Optional[List[str]] = None,
                         requirements_file: Optional[str] = None,
                         options: Optional[List[str]] = None,
                         verbose: bool = False) -> None:
        options = options or []
        command = [executable, "-m", "pip", "install"]
        if packages is not None:
            pass
        elif requirements_file is not None:
            req_path = Path(requirements_file)
            if not req_path.exists() or not req_path.is_file():
                raise BuilderError(f"File {requirements_file!r} does not "
                                   f"exist or was not recognized as a file.")
            with open(req_path, "r") as req_file:
                packages = req_file.readlines()
        else:
            raise BuilderError("Either a package list or a requirements "
                               "file need to be specified to the install "
                               "command.")
        command += list(packages)
        options += self.pip_install_options
        options += [f"--find-links={loc}" for loc in self.wheel_caches]
        command += list(set(options))

        location = Path(executable).parents[1]
        pkgs = ", ".join(packages)
        print(f"Installing packages {pkgs} into virtual environment"
              f" in location {location}.....", end="")
        self.run_subprocess(command)
        # this only runs if the subprocess succeeds
        print("done.")
        print(f"Successfully installed packages {pkgs} into virtual "
              f"environment in location {location}.")

    def uninstall_packages(self,
                           executable: str,
                           packages: List[str],
                           options: Optional[List[str]] = None,
                           verbose: bool = False) -> None:
        options = options or []
        options += self.pip_uninstall_options
        command = [executable, "-m", "pip", "uninstall", *packages]
        command += list(set(options))

        pkgs = ", ".join(packages)
        location = Path(executable).parents[1]
        print(f"Uninstalling packages {pkgs} from virtual environment"
              f" in location {location}.....", end="")
        self.run_subprocess(command)
        # this only runs if the subprocess succeeds
        print("done.")
        print(f"Successfully uninstalled packages {pkgs} from virtual "
              f"environment in location {location}.")

    def list_packages(self, executable: str,
                      verbose: bool = False) -> List[str]:
        command = [executable, "-m", "pip", "list", "--format=freeze"]

        rc, pip_output = self.run_subprocess(command, print_status=False)

        return pip_output.splitlines()
        # `pip list` output: table header, separator, package list
        # _, packages = flat_pkg_table[0], flat_pkg_table[2:]
        # return lmap(lambda x: "==".join(x.split()[:2]), packages)
