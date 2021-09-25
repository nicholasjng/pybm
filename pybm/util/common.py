from typing import List, Iterable, Tuple, Callable, TypeVar

T = TypeVar('T')
S = TypeVar('S')


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
    true_list = lfilter(lambda x: fn(x), iterable)
    false_list = lfilter(lambda x: not fn(x), iterable)
    return true_list, false_list


def tpartition(fn: Callable[[S], bool], iterable: Iterable[S]) -> \
        Tuple[Tuple[S, ...], Tuple[S, ...]]:
    true_list = tfilter(lambda x: fn(x), iterable)
    false_list = tfilter(lambda x: not fn(x), iterable)
    return true_list, false_list


def split_list(_l: list, n: int):
    return [_l[:n], _l[n:]]


def version_tuple(version: str):
    return tmap(int, version.split("."))


def version_string(x: Iterable):
    return ".".join(map(str, x))
