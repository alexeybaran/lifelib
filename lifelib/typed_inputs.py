"""Python reference operations for named numeric tables in scalar models."""

from bisect import bisect_right
from .immutable_inputs import Table


_MISSING = object()


def _column(table, column):
    return table['columns'].index(column) if isinstance(column, str) else column


def lookup(table, key, column, default=_MISSING):
    if isinstance(table, Table):
        try:
            return table.lookup(key, column)
        except KeyError:
            if default is _MISSING:
                raise
            return default
    try:
        index = table['keys'].index(key)
    except ValueError:
        if default is _MISSING:
            raise KeyError(key) from None
        return default
    return table['values'][index][_column(table, column)]


def previous(table, key, column, default=_MISSING):
    if isinstance(table, Table):
        if not table['keys'] or key < first_key(table):
            if default is _MISSING:
                raise ValueError(f'No key at or before {key!r}')
            return default
        return table.previous(key, column)
    index = bisect_right(table['keys'], key) - 1
    if index < 0:
        if default is _MISSING:
            raise ValueError(f'No key at or before {key!r}')
        return default
    return table['values'][index][_column(table, column)]


def contains(table, key):
    if isinstance(table, Table):
        return table.contains(key)
    return key in table['keys']


def key_count(table):
    return len(table['keys'])


def key_at(table, index):
    if index < 0:
        raise IndexError(index)
    return table['keys'][index]


def first_key(table):
    return min(table['keys'])


def last_key(table):
    return max(table['keys'])


def subtable(table, key):
    return table[key]


def has_group(table, key):
    return key in table


def sum_f64(values):
    return sum(values, 0.0)


def sum_helper(values):
    return sum(values, 0.0)


for _operation in (lookup, previous, contains, key_count, key_at, first_key,
                   last_key, subtable, has_group, sum_f64, sum_helper):
    _operation.__modelx_native_operation__ = _operation.__name__
    _operation.__modelx_cython_helper__ = ('lifelib._native_inputs', _operation.__name__)

_native_operations = {function.__name__: function for function in
                      (lookup, previous, contains, key_count, key_at, first_key,
                       last_key, subtable, has_group, sum_f64, sum_helper)}

sum_f64.__modelx_cython_reduction__ = 'f64_sum'
lookup.__modelx_cython_numeric__ = 'lookup_f64'
previous.__modelx_cython_numeric__ = 'previous_f64'
