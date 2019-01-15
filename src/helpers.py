import os
import itertools
import datetime
from functools import wraps
from typing import Callable, Union, List, Tuple
from sc2 import Result


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


def property_cache_forever(f):
    """Decorator that caches class properties"""
    f.cached = None

    @wraps(f)
    def inner(self):
        if f.cached is None:
            f.cached = f(self)
        return f.cached
    return property(inner)


def get_timestamp():
    return datetime.datetime.now().isoformat()


def sanitize_for_file(s):
    """
    >>> sanitize_for_file('58:20.10')
    '58-20_10'
    """
    return str(s).replace(':', '-').replace('.', '_')


def get_filesafe_timestamp():
    return sanitize_for_file(get_timestamp())


def get_replay_name(players, game_map) -> str:
    replay_part = None
    if hasattr(players[1], 'difficulty'):
        replay_part = '{}-{}-vs-{}-{}'.format(
            game_map.name, players[0].__class__.__name__, players[1].race, players[1].difficulty)
    else:
        replay_part = '{}-{}-vs-{}'.format(
            game_map.name, players[0].__class__.__name__, players[1].race)
    replay_name = os.path.join(
        os.getcwd(), 'replays', '{}_{}'.format(get_filesafe_timestamp(), replay_part))
    sanitized_replay_name = replay_name.replace('.', '_')
    return '{}.SC2Replay'.format(sanitized_replay_name)


def get_plot_directory() -> str:
    return os.path.join(os.getcwd(), 'plots')


def get_figure_name(game_result: Result) -> str:
    """Gets a unique name for a figure."""
    file_name = '{}_{}'.format(game_result.name, get_filesafe_timestamp())
    path_name = get_plot_directory()
    figure_name = os.path.join(path_name, file_name)
    return figure_name


def make_dir_if_not_exists(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
