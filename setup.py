from setuptools import setup, find_packages


def get_requirements() -> list[str]:
    with open("requirements.txt", "r") as f:
        return f.readlines()


def get_extras():
    """Extra pybm functionality, specified as a valid argument to
    setuptools.setup's 'extras_require' keyword argument."""
    extra_features = {
        "gbm": ["google_benchmark @ git+https://github.com/google/benchmark"]
    }
    extra_features["all"] = sum(extra_features.values(), start=[])
    return extra_features


def get_version(fp) -> str:
    with open(fp, "r") as f:
        for line in f:
            if "version" in line:
                delim = '"'
                return line.split(delim)[1]
    raise RuntimeError(f"could not find a valid version string in {fp}.")


setup(
    name="pybm",
    version=get_version("pybm/__init__.py"),
    description="A Python CLI for reproducible benchmarking in a git repository.",
    packages=find_packages(),
    install_requires=get_requirements(),
    extras_require=get_extras(),
    entry_points={"console_scripts": ["pybm=pybm.main:main"]},
    exclude=["tests"],
    author="Nicholas Junge",
    license="Apache-2.0",
    url="https://github.com/nicholasjng/pybm",
)
