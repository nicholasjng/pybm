def get_extras():
    """Extra pybm functionality, specified as a valid argument to
    setuptools.setup's 'extras_require' keyword argument."""
    extra_features = {"gbm": ["pybm", "google-benchmark"]}
    extra_features["all"] = sum(extra_features.values(), [])
    return extra_features
