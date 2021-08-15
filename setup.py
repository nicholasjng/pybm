from setuptools import setup, find_packages


def get_requirements() -> list[str]:
    with open("requirements.txt", "r") as f:
        reqs = f.readlines()
    return reqs


def get_version(fp) -> str:
    with open(fp, "r") as f:
        for line in f:
            if "version" in line:
                delim = "\""
                return line.split(delim)[1]
    raise RuntimeError(f"could not find a valid version string in {fp}.")


setup(
    name="pybm",
    version=get_version("pybm/__init__.py"),
    description="A Python CLI for reproducible benchmarking in a git "
                "repository.",
    packages=find_packages(),
    install_requires=get_requirements(),
    entry_points={
        'console_scripts': ['pybm=pybm.main:main']
    },
    author="Nicholas Junge",
    license="Apache-2.0",
    url="https://github.com/njunge94/pybm"
)
