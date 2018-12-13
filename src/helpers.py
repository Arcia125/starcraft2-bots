import itertools
from functools import wraps
from typing import Callable, Union, List, Tuple


def longest_list_index(target_list: List) -> int:
    """Returns the longest list index in target_list
    >>> longest_list_index([[1,2,3], [1,2], [1,2,3,4], [9]])
    2
    >>> longest_list_index([['A', 'D', 'F'], ['B', 'E'], [4], ['C', '2', '4', '5']])
    3
    >>> longest_list_index([])
    0
    >>> longest_list_index()
    Traceback (most recent call last):
        ...
    TypeError: longest_list_index() missing 1 required positional argument: 'target_list'
    """
    highest = 0
    highest_index = 0
    for i, val in enumerate(target_list):
        length = len(val)
        if length > highest:
            highest = length
            highest_index = i
    return highest_index


def roundrobin(*lists):
    """Takes any number of iterables and combines them into an alternating pattern
    >>> roundrobin(['A', 'D', 'F'], ['B', 'E'], ['C'])
    ['A', 'B', 'C', 'D', 'E', 'F']
    >>> roundrobin(['a', 'b', 'c', 'd'], ['One', 'Two', 'Three'], [1, 2, 3, 4, 5, 6, 7, 8])
    ['a', 'One', 1, 'b', 'Two', 2, 'c', 'Three', 3, 'd', 4, 5, 6, 7, 8]
    >>> roundrobin([1, 2, 3], [4, 5, 6])
    [1, 4, 2, 5, 3, 6]
    """
    result = []
    all_lists = list(lists)
    index_of_longest_list = longest_list_index(all_lists)
    for index, item in enumerate(all_lists[index_of_longest_list]):
        for l in all_lists:
            try:
                result.append(l[index])
            except IndexError as e:
                pass
    return result


def between(value: Union[int, float], minimum: Union[int, float], maximum: Union[int, float]) -> bool:
    """
    >>> between(50, 30, 60)
    True
    >>> between(5, 0, 10)
    True
    >>> between(5, 0, 4)
    False
    """
    return minimum < value < maximum


def value_between_any(value: Union[int, float], items: List[Tuple[Union[int, float], Union[int, float]]]) -> bool:
    """Returns whether the given value falls between any of the ranges in the given list.
    >>> value_between_any(5, [(1, 6)])
    True
    >>> value_between_any(10, [(1, 6), (6, 12)])
    True
    >>> value_between_any(100, [(1, 6), (6, 12)])
    False
    """
    return any(between(value, minimum, maximum) for minimum, maximum in items)


def property_cache_forever(f):
    f.cached = None

    @wraps(f)
    def inner(self):
        if f.cached is None:
            f.cached = f(self)
        return f.cached
    return property(inner)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
