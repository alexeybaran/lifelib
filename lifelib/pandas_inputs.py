"""Explicit pandas-to-owned-input preparation for ordinary modelx Data Cells.

Calculation helpers live in :mod:`lifelib.typed_inputs` and operate on the
existing Table/Record structures in every execution mode. Public pandas inputs
remain separate. Preparation follows normal modelx dependency/cache rules.
"""
from collections import OrderedDict

import numpy as np
import pandas as pd

from .immutable_inputs import Record, Table, freeze


def _scalar(value):
    # itertuples preserves per-column scalar values; iterrows would coerce a
    # numeric mixed row to one dtype before the explicit preparation boundary.
    if isinstance(value, np.generic):
        value = value.item()
    return freeze(value)


def _key(value):
    if isinstance(value, tuple):
        return tuple(_key(part) for part in value)
    return _scalar(value)


def table(frame, *, columns=None, groups=()):
    """Build an existing Table, optionally nested in explicit group Records.

    ``groups`` names index levels to group, in the authored nesting order. The
    remaining index levels form leaf keys. Row order and named column order are
    retained. This constructor does not sort, fill missing values, aggregate
    duplicates or coerce every numeric column to float. Those are separate
    operations, never implicit preparation policies.

    The normal Table contract requires unique leaf keys and nonempty unique
    string columns. Unsupported scalar values raise rather than silently lose
    their dtype/missing semantics. Public DataFrames are not modified.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError('table requires a pandas DataFrame')
    selected = list(frame.columns) if columns is None else list(columns)
    if not selected or any(type(name) is not str for name in selected):
        raise ValueError('table columns must be nonempty strings')
    if len(set(selected)) != len(selected) or not frame.columns.is_unique:
        raise ValueError('table columns must be unique')
    selected_frame = frame.loc[:, selected]
    names = list(frame.index.names)
    groups = tuple(groups)
    if len(set(groups)) != len(groups):
        raise ValueError('group levels must be unique')
    if any(names.count(level) != 1 for level in groups):
        raise ValueError('group levels must name unique index levels')
    grouped_positions = [names.index(level) for level in groups]
    remaining_positions = [i for i in range(frame.index.nlevels)
                           if i not in grouped_positions]
    if groups and not remaining_positions:
        raise ValueError('grouping must leave at least one leaf key level')
    root = OrderedDict() if groups else []
    for label, row in zip(frame.index, selected_frame.itertuples(index=False, name=None)):
        parts = tuple(label) if isinstance(frame.index, pd.MultiIndex) else (label,)
        parts = tuple(_key(part) for part in parts)
        leaf_parts = tuple(parts[i] for i in remaining_positions)
        key = leaf_parts[0] if len(leaf_parts) == 1 else leaf_parts
        value = tuple(_scalar(item) for item in row)
        if not groups:
            root.append((key, value))
            continue
        branch = root
        for position in grouped_positions[:-1]:
            branch = branch.setdefault(parts[position], OrderedDict())
        branch.setdefault(parts[grouped_positions[-1]], []).append((key, value))

    def build(branch, depth):
        if depth == len(groups):
            return Table([key for key, _ in branch],
                         [values for _, values in branch], selected)
        return Record({key: build(value, depth + 1) for key, value in branch.items()})
    return build(root, 0)


def records(frame):
    """Prepare owned row Records keyed by the frame index, without row coercion."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError('records requires a pandas DataFrame')
    if not frame.index.is_unique:
        raise ValueError('duplicate record key')
    columns = tuple(frame.columns)
    if not frame.columns.is_unique:
        raise ValueError('record columns must be unique')
    return Record({_key(key): Record({column: _scalar(value)
                   for column, value in zip(columns, row)})
                   for key, row in zip(frame.index, frame.itertuples(index=False, name=None))})


def record(row):
    """Prepare a Record from an explicitly selected public pandas Series.

    A model can keep its public model_point Cell unchanged and make a separate
    preparation Cell depend on that value. Its mixed-row coercion/name semantics
    stay in the public pandas selection; calculation reads the owned fields.
    """
    if not isinstance(row, pd.Series):
        raise TypeError('record requires a pandas Series')
    if not row.index.is_unique:
        raise ValueError('record fields must be unique')
    return Record({key: _scalar(value) for key, value in row.items()})
