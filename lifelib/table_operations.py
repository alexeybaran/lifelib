"""Explicit row/column expressions over the existing owned Table and Record.

Preparation and final pandas materialization are visible boundaries. Calculation
selection has direct Cython provider declarations, without formula recognition.
"""
from copy import deepcopy
from types import MappingProxyType

from .immutable_inputs import (Table, Record, _index_key, _index_error_key,
                               _valid_index_key)

_MISSING = object()


def row(table, key):
    """Select a unique labelled row, preserving prepared pandas row coercion."""
    if not isinstance(table, Table):
        raise TypeError('row requires an owned Table')
    metadata = table._metadata
    if metadata is None or metadata[0] != 'frame':
        raise ValueError('row requires a table prepared with pandas row metadata')
    try:
        if table._index_error is not None and not _valid_index_key(key, table._index_error):
            raise KeyError(key)
        position = table._positions[_index_key(key, table._index_error)]
    except KeyError:
        raise KeyError(_index_error_key(key, table._index_error)) from None
    # Metadata is already owned. Avoid freezing the scalars a second time; this
    # preserves pandas scalar identity, including nullable missing singletons.
    result = object.__new__(Record)
    items = tuple(zip(table._columns, metadata[4][position]))
    object.__setattr__(result, '_items', items)
    object.__setattr__(result, '_index', MappingProxyType(dict(items)))
    object.__setattr__(result, '_native_groups', {})
    object.__setattr__(result, '_metadata', ('row', metadata[2], metadata[5][position],
                                           metadata[8][position], metadata[6], metadata[7]))
    return result


def column(table, name):
    """Return ordered immutable values, with the existing column scalar types.

    This is a value sequence, not a public Series. No aggregation or missing-value
    policy is implied. Use to_pandas(table) to restore the labelled public report.
    """
    if not isinstance(table, Table):
        raise TypeError('column requires an owned Table')
    try:
        position = table._columns.index(name)
    except ValueError:
        raise KeyError(name) from None
    return tuple(values[position] for values in table._values)


def to_pandas(value, *, index_name=_MISSING):
    """Materialize owned report metadata into the public DataFrame or Series.

    Python/pandas execution at this output boundary is explicit and timed. Row
    and column calculations precede it. Untagged records are not guessed to be
    report rows, and tables without preserved metadata are rejected.
    """
    import pandas as pd
    if type(value) is Table:
        meta = value._metadata
        if meta is None or meta[0] != 'frame':
            raise ValueError('to_pandas requires preserved report metadata')
        index, columns, dtypes = meta[1].copy(deep=True), meta[2].copy(deep=True), meta[3]
        result = pd.DataFrame({name: pd.Series([row[i] for row in value._values],
                               index=index, dtype=dtypes[i])
                               for i, name in enumerate(value._columns)}, index=index)
        result.columns = columns
        result.attrs = deepcopy(meta[6])
        result.flags.allows_duplicate_labels = meta[7]
    elif type(value) is Record and value._metadata is not None and value._metadata[0] == 'row':
        meta = value._metadata
        result = pd.Series([entry[1] for entry in value._items],
                           index=meta[1].copy(deep=True), dtype=meta[2], name=meta[3])
        result.attrs = deepcopy(meta[4])
        result.flags.allows_duplicate_labels = meta[5]
    else:
        raise TypeError('to_pandas requires an owned report Table or row Record')
    if index_name is not _MISSING:
        result.index = result.index.rename(index_name)
    return result


for _function in (row, column):
    _function.__modelx_native_operation__ = _function.__name__
    _function.__modelx_cython_helper__ = ('lifelib._native_inputs', _function.__name__)
    _function.__modelx_cython_call_layout__ = 'keywords'
    _function.__modelx_cython_scalar_result__ = 'object'
