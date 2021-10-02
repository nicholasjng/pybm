import re
from typing import List, Iterable, Tuple, Callable, TypeVar, Dict

T = TypeVar('T')
S = TypeVar('S')
U = TypeVar('U')
V = TypeVar('V')


def lmap(fn: Callable[[S], T], iterable: Iterable[S]) -> List[T]:
    return list(map(fn, iterable))


def tmap(fn: Callable[[S], T], iterable: Iterable[S]) -> Tuple[T, ...]:
    return tuple(map(fn, iterable))


def lfilter(fn: Callable[[S], bool], iterable: Iterable[S]) -> List[S]:
    return list(filter(fn, iterable))


def tfilter(fn: Callable[[S], bool], iterable: Iterable[S]) -> Tuple[S, ...]:
    return tuple(filter(fn, iterable))


def lpartition(fn: Callable[[S], bool], iterable: Iterable[S]) -> \
        Tuple[List[S], List[S]]:
    """Partition list into two with a boolean function. Not particularly
    efficient because of the double pass, but fine for small lists."""
    true_list = lfilter(lambda x: fn(x), iterable)
    false_list = lfilter(lambda x: not fn(x), iterable)
    return true_list, false_list


def tpartition(fn: Callable[[S], bool], iterable: Iterable[S]) -> \
        Tuple[Tuple[S, ...], Tuple[S, ...]]:
    """Partition tuple into two with a boolean function. Not particularly
    efficient because of the double pass, but fine for small tuples."""
    true_list = tfilter(lambda x: fn(x), iterable)
    false_list = tfilter(lambda x: not fn(x), iterable)
    return true_list, false_list


def dkmap(fn: Callable[[S], T], dictionary: Dict[S, U]) -> Dict[T, U]:
    return {fn(k): v for k, v in dictionary.items()}


def dvmap(fn: Callable[[U], T], dictionary: Dict[S, U]) -> Dict[S, T]:
    return {k: fn(v) for k, v in dictionary.items()}


def dmap(fn: Callable[[S, T], Tuple[U, V]], dictionary: Dict[S, T]) \
        -> Dict[U, V]:
    return {k: v for k, v in map(fn, dictionary.keys(), dictionary.values())}


def dkfilter(fn: Callable[[S], bool], dictionary: Dict[S, T]) -> Dict[S, T]:
    return {k: dictionary[k] for k in lfilter(fn, dictionary.keys())}


def dfilter(fn: Callable[[Tuple[S, T]], bool], dictionary: Dict[S, T]) \
        -> Dict[S, T]:
    return {k: v for k, v in tfilter(fn, dictionary.items())}


def split_list(_l: List[T], n: int) -> Tuple[List[T], List[T]]:
    return _l[:n], _l[n:]


def version_tuple(version: str):
    return tmap(int, version.split("."))


def version_string(x: Iterable):
    return ".".join(map(str, x))


def lfilter_regex(expr: str, iterable: Iterable[str]) -> List[str]:
    pattern = re.compile(expr)
    return lfilter(lambda x: pattern.search(x) is not None, iterable)


def dfilter_regex(expr: str, dictionary: Dict[str, T]) -> Dict[str, T]:
    pattern = re.compile(expr)
    return dkfilter(lambda x: pattern.search(x) is not None, dictionary)


def flatten(t):
    return [item for sublist in t for item in sublist]


def partition_n(n: int, fn: Callable[[T], int], listlike: Iterable[T]) \
        -> List[List[T]]:
    return_obj: List[List[T]] = [[] for _ in range(n)]
    for elem in listlike:
        k = fn(elem)
        assert 0 <= k < n, "partition function needs to return an integer " \
                           "in the interval [0, {n})."
        return_obj[k].append(elem)
    return return_obj
