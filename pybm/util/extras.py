def get_extras():
    """Extra pybm functionality, specified as a valid argument to
    setuptools.setup's 'extras_require' keyword argument."""
    extra_features = {
        "gbm": ["google-benchmark==0.2.0"]
    }
    extra_features["all"] = sum(extra_features.values(), start=[])
    return extra_features
