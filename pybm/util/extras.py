from typing import List, Dict

from pybm.specs import Package


def get_extras():
    """Extra pybm functionality, specified as a valid argument to
    setuptools.setup's 'extras_require' keyword argument."""
    extra_features: Dict[str, List[Package]] = {
        "gbm": [
            Package("pybm", origin="https://github.com/nicholasjng/pybm"),
            Package("google-benchmark"),
        ]
    }
    # be explicit here for mypy
    start: List[Package] = []
    extra_features["all"] = sum(extra_features.values(), start)
    return extra_features
