import re
from pybm.util.imports import import_module_from_source
from pybm.util.common import dfilter


def f():
    print("hello from f")


def f2():
    print("hello from f2")


def g():
    print("hello from g")


if __name__ == "__main__":
    pattern = re.compile("f.*")
    print(f.__module__)
    print(import_module_from_source.__module__)
    print(globals())
    print(dfilter(lambda x: pattern.match(x[0]) is not None, globals()))
