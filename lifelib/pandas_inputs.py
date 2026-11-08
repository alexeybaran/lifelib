"""Explicit owned numeric inputs; public tables remain ordinary pandas objects.

``numeric_table(frame)`` takes a snapshot at the authored preparation boundary.
``lookup(table, key, column)`` means ``float(snapshot.loc[key, column])``.
This module does not alter pandas indexing, alignment or report contracts.
"""
import builtins

import numpy as np
import pandas as pd


class NumericTable:
    """Owned snapshot with disposable native resources and pandas fallback.

    Preparation is explicit. A changed source requires a new snapshot (normally
    by invalidating its modelx preparation Cell). Public pandas inputs are never
    silently treated as immutable.
    """
    __slots__ = ('_frame', '_keys', '_columns', '_values', '_native_ready')

    def __init__(self, frame):
        if not isinstance(frame, pd.DataFrame):
            raise TypeError('numeric_table requires a pandas DataFrame')
        self._frame = frame.copy(deep=True)
        self._keys = self._columns = self._values = None
        self._native_ready = False
        # Native admission is conservative; fallback keeps full pandas semantics.
        # Extension arrays, subclass hooks and duplicates are not assumed plain.
        if (type(frame) is not pd.DataFrame
                or type(frame.index) not in (pd.Index, pd.RangeIndex, pd.MultiIndex)
                or type(frame.columns) is not pd.Index or not frame.index.is_unique
                or not frame.columns.is_unique
                or not all(type(c) is str for c in frame.columns)):
            return
        keys = tuple(frame.index)
        if not all(_plain_key(key) for key in keys):
            return
        columns = [column for column, dtype in frame.dtypes.items()
                   if isinstance(dtype, np.dtype) and dtype.kind in 'biuf' and dtype.itemsize <= 8]
        if not columns:
            return
        self._keys = dict(zip(keys, range(len(keys))))
        self._columns = dict(zip(columns, range(len(columns))))
        self._values = np.array(self._frame[columns].to_numpy(), dtype=np.float64, order='C', copy=True)
        self._values.flags.writeable = False
        self._native_ready = True

    def __reduce__(self):
        # Native views/maps are reconstructed, never serialized as hidden state.
        return type(self), (self._frame,)


def _plain_key(key):
    return (type(key) in (str, int) or
            type(key) is tuple and all(_plain_key(part) for part in key))


def numeric_table(frame):
    """Prepare an owned snapshot; retain unsupported layouts through pandas."""
    return NumericTable(frame)


def lookup(table, key, column):
    """Return float(snapshot.loc[key, column]), including pandas exceptions."""
    if type(table) is not NumericTable:
        raise TypeError('lookup requires a numeric_table snapshot')
    return builtins.float(table._frame.loc[key, column])


lookup.__modelx_cython_helper__ = ('lifelib._native_pandas', 'lookup')
lookup.__modelx_cython_numeric__ = 'lookup_f64'
