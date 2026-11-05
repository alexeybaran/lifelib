"""Python reference operations for named numeric tables in scalar models."""

from bisect import bisect_right


_MISSING = object()


def _column(table, column):
    return table['columns'].index(column) if isinstance(column, str) else column


def lookup(table, key, column, default=_MISSING):
    try:
        index = table['keys'].index(key)
    except ValueError:
        if default is _MISSING:
            raise KeyError(key) from None
        return default
    return table['values'][index][_column(table, column)]


def previous(table, key, column, default=_MISSING):
    index = bisect_right(table['keys'], key) - 1
    if index < 0:
        if default is _MISSING:
            raise ValueError(f'No key at or before {key!r}')
        return default
    return table['values'][index][_column(table, column)]


def contains(table, key):
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
