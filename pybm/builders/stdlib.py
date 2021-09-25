"""
Virtual environment creation class for benchmarking
with custom requirements in Python."""
from pathlib import Path
import shutil
from typing import List, Optional, Union

from pybm.builders import PythonEnvBuilder
from pybm.config import PybmConfig
from pybm.specs import EnvSpec
from pybm.util.common import lmap, version_string
from pybm.exceptions import BuilderError


# TODO: Subclass directly from venv.EnvBuilder instead of going the
#  subprocess route
class PythonStdlibBuilder(PythonEnvBuilder):
    """Python standard library virtual environment builder class."""

    def __init__(self, config: PybmConfig):
        super().__init__(config=config)
        self.venv_home: str = config.get_value("builder.homeDirectory")
        self.venv_options: str = config.get_value(
            "builder.persistentVenvOptions")
        self.pip_install_options: str = config.get_value(
            "builder.persistentPipInstallOptions")
        self.pip_uninstall_options: str = config.get_value(
            "builder.persistentPipUninstallOptions")

    def create(self,
               executable: str,
               destination: str,
               options: Optional[List[str]] = None) -> EnvSpec:
        # create the venv in the worktree or in a special home directory
        if self.venv_home == "":
            env_dir = Path(destination) / "venv"
        else:
            env_dir = (Path(self.venv_home) / destination).parent.resolve()

        command = [executable, "-m", "venv", str(env_dir)]
        option_list = []
        if options is not None:
            option_list += options
        if self.venv_options != "":
            option_list += self.venv_options.split(",")

        # Prevent duplicate options
        command += list(set(option_list))
        print(f"Creating virtual environment in directory {env_dir}.....",
              end="")
        self.run_subprocess(command)
        print("done.")

        executable = self.get_executable(env_dir)
        python_version = version_string(self.get_python_version(executable))
        return EnvSpec(root=str(env_dir),
                       executable=executable,
                       python_version=python_version,
                       packages=self.list_packages(executable))

    @staticmethod
    def delete(env_dir: str) -> None:
        def onerror(ex_type, value, traceback):
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
        path = Path(self.venv_home) / env_dir
        if not self.is_valid_venv(path, verbose=verbose):
            msg = f"The specified path {env_dir} was not recognized " \
                  f"as a valid virtual environment, since no `python`/" \
                  f"`pip` executables or symlinks were discovered."
            raise BuilderError(msg)
        print(f"Successfully linked existing virtual environment in location "
              f"{env_dir}.")
        executable = self.get_executable(env_dir)
        python_version = version_string(self.get_python_version(executable))
        return EnvSpec(root=str(env_dir),
                       executable=executable,
                       python_version=python_version,
                       packages=self.list_packages(executable))

    def install_packages(self,
                         root: str,
                         packages: Optional[List[str]] = None,
                         requirements_file: Optional[str] = None,
                         options: Optional[List[str]] = None,
                         verbose: bool = False):
        executable = self.get_executable(root)
        command = [executable, "-m", "pip", "install"]
        if packages is not None:
            packages = packages
        elif requirements_file is not None:
            req_path = Path(requirements_file)
            if not req_path.exists():
                raise BuilderError(f"File {requirements_file} does not "
                                   f"exist.")
            with open(req_path, "r") as req_file:
                packages = req_file.readlines()
        else:
            raise BuilderError("Either a package list or a requirements "
                               "file need to be specified to the install "
                               "command.")
        command += list(packages)
        option_list = []
        if options is not None:
            option_list += options
        if self.pip_install_options != "":
            option_list += self.pip_install_options.split(",")
        if self.wheel_caches != "":
            cache_locations = self.wheel_caches.split(":")
            option_list += [f"--find-links={loc}" for loc in cache_locations]
        command += list(set(option_list))

        print(f"Installing packages `{packages}` into virtual environment"
              f" in location {root}.....", end="")
        self.run_subprocess(command)
        # this only runs if the subprocess succeeds
        print("done.")
        print("Successfully installed packages {pkgs}".format(
            pkgs=", ".join(packages)))
        return self.list_packages(executable=executable)

    def uninstall_packages(self,
                           root: str,
                           packages: List[str],
                           options: Optional[List[str]] = None,
                           verbose: bool = False):
        executable = self.get_executable(root=root)
        command = [executable, "-m", "pip", "uninstall", *packages]
        option_list = []
        if options is not None:
            option_list += options
        if self.pip_uninstall_options != "":
            option_list += self.pip_uninstall_options.split(",")
        command += list(set(option_list))

        pkgs = ", ".join(packages)
        print(f"Uninstalling packages {pkgs} from virtual environment"
              f" in location {root}.....", end="")
        self.run_subprocess(command)
        # this only runs if the subprocess succeeds
        print("done.")
        print(f"Successfully uninstalled packages {pkgs} from virtual "
              f"environment in location {root}.")
        return self.list_packages(executable=executable)

    def list_packages(self, executable: str) -> List[str]:
        command = [executable, "-m", "pip", "list"]

        rc, pip_output = self.run_subprocess(command, print_status=False)

        flat_pkg_table = pip_output.splitlines()
        # `pip list` output: table header, separator, package list
        _, packages = flat_pkg_table[0], flat_pkg_table[2:]
        return lmap(lambda x: "==".join(x.split()[:2]), packages)
