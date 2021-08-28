import pathlib
from pathlib import Path


def get_subdirs():
    p = pathlib.Path()
    # All subdirectories in the current directory, not recursive.
    all_subdirs = [f.stem for f in filter(Path.is_dir, p.iterdir())]
