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
    true_list = lfilter(lambda x: fn(x), iterable)
    false_list = lfilter(lambda x: not fn(x), iterable)
    return true_list, false_list


def tpartition(fn: Callable[[S], bool], iterable: Iterable[S]) -> \
        Tuple[Tuple[S, ...], Tuple[S, ...]]:
    true_list = tfilter(lambda x: fn(x), iterable)
    false_list = tfilter(lambda x: not fn(x), iterable)
    return true_list, false_list


def dkmap(fn: Callable[[S], T], dictionary: Dict[S, U]) -> Dict[T, U]:
    return {fn(k): v for k, v in dictionary.items()}


def dvmap(fn: Callable[[U], T], dictionary: Dict[S, U]) -> Dict[S, T]:
    return {k: fn(v) for k, v in dictionary.items()}


def dmap(fn: Callable[[Tuple[S, T]], Tuple[U, V]], dictionary: Dict[S, T]) \
        -> Dict[U, V]:
    return {k: v for k, v in tmap(fn, dictionary.items())}


def dfilter(fn: Callable[[Tuple[S, T]], bool], dictionary: Dict[S, T]) \
        -> Dict[S, T]:
    return {k: v for k, v in tfilter(fn, dictionary.items())}


def split_list(_l: List[T], n: int) -> Tuple[List[T], List[T]]:
    return _l[:n], _l[n:]


def version_tuple(version: str):
    return tmap(int, version.split("."))


def version_string(x: Iterable):
    return ".".join(map(str, x))
