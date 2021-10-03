import pybm


def f():
    return sum(range(100000))


if __name__ == "__main__":
    pybm.run(context=globals())
