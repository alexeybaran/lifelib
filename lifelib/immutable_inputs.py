"""Owned immutable records and keyed tables for model inputs.

Construction is explicit: existing dictionaries and pandas objects are never
silently frozen. Keys and authored enum objects retain their Python identity.
"""
from bisect import bisect_right
from collections.abc import Mapping
from types import MappingProxyType


class Record(Mapping):
    __slots__ = ('_items', '_index')

    def __init__(self, values):
        items = tuple((key, freeze(value)) for key, value in values.items())
        object.__setattr__(self, '_items', items)
        object.__setattr__(self, '_index', MappingProxyType(dict(items)))

    def __setattr__(self, name, value):
        raise AttributeError('immutable input')

    def __delattr__(self, name):
        raise AttributeError('immutable input')

    def __getitem__(self, key):
        return self._index[key]

    def __iter__(self):
        return iter(self._index)

    def __len__(self):
        return len(self._index)

    def __reduce__(self):
        return type(self), (dict(self._items),)

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self


class Table(Mapping):
    __slots__ = ('_keys', '_values', '_columns', '_positions', '_ordered')

    def __init__(self, keys, values, columns):
        keys, columns = tuple(keys), tuple(columns)
        values = tuple(tuple(freeze(value) for value in row) for row in values)
        if not columns or len(set(columns)) != len(columns):
            raise ValueError('table columns must be nonempty and unique')
        if any(type(column) is not str for column in columns):
            raise TypeError('table columns must be strings')
        if len(keys) != len(values) or any(len(row) != len(columns) for row in values):
            raise ValueError('table dimensions do not match')
        positions = dict(zip(keys, range(len(keys))))
        if len(positions) != len(keys):
            raise ValueError('duplicate table key')
        object.__setattr__(self, '_keys', keys)
        object.__setattr__(self, '_values', values)
        object.__setattr__(self, '_columns', columns)
        object.__setattr__(self, '_positions', MappingProxyType(positions))
        try:
            ordered = tuple(sorted(keys))
        except TypeError:
            ordered = None
        object.__setattr__(self, '_ordered', ordered)

    def __setattr__(self, name, value):
        raise AttributeError('immutable input')

    def __delattr__(self, name):
        raise AttributeError('immutable input')

    def __getitem__(self, key):
        if key == 'keys':
            return self._keys
        if key == 'values':
            return self._values
        if key == 'columns':
            return self._columns
        raise KeyError(key)

    def __iter__(self):
        return iter(('keys', 'values', 'columns'))

    def __len__(self):
        return 3

    def lookup(self, key, column):
        position = self._positions[key]
        column = self._columns.index(column) if isinstance(column, str) else column
        return self._values[position][column]

    def previous(self, key, column):
        if self._ordered is None:
            raise TypeError('predecessor lookup requires ordered keys')
        index = bisect_right(self._ordered, key) - 1
        if index < 0:
            raise ValueError(f'No key at or before {key!r}')
        return self.lookup(self._ordered[index], column)

    def contains(self, key):
        return key in self._positions

    def __reduce__(self):
        return type(self), (self._keys, self._values, self._columns)

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self


def freeze(value):
    if isinstance(value, (Record, Table)):
        return value
    if type(value) is dict:
        if value.keys() == {'keys', 'values', 'columns'}:
            return Table(value['keys'], value['values'], value['columns'])
        return Record(value)
    if type(value) in (tuple, list):
        return tuple(freeze(item) for item in value)
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return value
    raise TypeError(f'unsupported immutable input value: {type(value).__name__}')
