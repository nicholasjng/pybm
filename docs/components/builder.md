# The builder component

The `Builder` class component of `pybm` is responsible for managing a Python virtual environment throughout its
lifecycle. The main lifecycle management aspects are creation, deletion, installation and uninstallation.

An abstract base class interface is the `pybm.builders.BaseBuilder`.

## Creating a virtual environment

Creation of a Python virtual environment works through the `Builder.create` API.

```python
def create(
        self,
        executable: Union[str, Path],
        destination: Union[str, Path],
        options: Optional[List[str]] = None,
        verbose: bool = False,
) -> PythonSpec:
```

The `executable` argument is the path to the Python executable which is used to create the virtual environment.
The `destination` argument gives the desired disk location for the new virtual environment.

`options` is a list of command line options passed to the virtual environment creation tool (by default, this is
Python's own `venv`, but could also be something else). The `verbose` parameter can be used to output diagnostic
information during the creation process.

The return object of this function is a `PythonSpec`, a dataclass containing the essential information around a virtual
environment (location, Python version, installed packages). The class definition is as follows:

```python
# pybm/specs.py

@dataclass(frozen=True)
class PythonSpec:
    """Dataclass representing a Python virtual environment."""

    root: str = field()
    executable: str = field()
    version: str = field()
    packages: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)

    def update_packages(self, packages: List[str]):
        self.packages.clear()
        self.packages.extend(packages)
```

`root` is the location of the virtual environment, `executable` is the Python executable tied to the venv, `version` is
the Python version, `packages` is the list of installed packages (with versions), `locations` is an optional list of
locations of extra locally installed packages.

## Deleting a virtual environment

Deletion of a Python virtual environment works through the `Builder.delete` API.

```python
def def delete(
    self,
    env_dir: Union[str, Path]

,
verbose: bool = False
) -> None:
```

To delete a virtual environment, simply pass its physical location on disk as the `env_dir` variable. Other variables
work exactly as before.

## Installing packages into a virtual environment

Installing packages into a Python virtual environment works through the `Builder.install` API.

```python
def install(
        self,
        spec: PythonSpec,
        packages: Optional[List[str]] = None,
        requirements_file: Optional[str] = None,
        options: Optional[List[str]] = None,
        verbose: bool = False,
) -> None:
```

Here, `spec` is the `PythonSpec` instance representing the virtual environment of interest. Packages can either be
specified as a list (the `packages` argument), or from a requirements file (the `requirements_file` argument). Options
can be passed through to the virtual environment tool with the `options` argument, the default package managing solution
for installation with the `venv` builder is `pip install`.

## Uninstalling packages from a virtual environment

Uninstalling packages from a Python virtual environment works through the `Builder.uninstall` API.

```python
def uninstall(
        self,
        spec: PythonSpec,
        packages: List[str],
        options: Optional[List[str]] = None,
        verbose: bool = False,
) -> None:
    raise NotImplementedError
```

Here, `spec` is again the `PythonSpec` instance representing the virtual environment of interest. Packages are specified
as a list (the `packages` argument). Options can be passed through to the virtual environment tool with the `options`
argument, the default package managing solution for uninstallation with the `venv` builder is `pip uninstall`.

## Listing installed packages of a virtual environment

Listing installed packages of a Python virtual environment works through the `Builder.list` API.

```python
def list(
        self,
        executable: Union[str, Path],
        verbose: bool = False
) -> List[str]:
    raise NotImplementedError
```

Here, `executable` is the path to the virtual environment's Python executable, found in the `bin` folder (on Linux and
macOS) or the `Scripts` folder (Windows).