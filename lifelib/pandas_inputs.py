"""Explicit pandas-to-owned-input preparation for ordinary modelx Data Cells.

Calculation helpers live in :mod:`lifelib.typed_inputs` and operate on the
existing Table/Record structures in every execution mode. Public pandas inputs
remain separate. Preparation follows normal modelx dependency/cache rules.
"""
from collections import OrderedDict
from copy import deepcopy

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


def table(frame, *, columns=None, groups=(), indexing='loc', rows=False, report=False):
    """Build an existing Table, optionally nested in explicit group Records.

    ``groups`` names index levels to group, in the authored nesting order. The
    remaining index levels form leaf keys. Row order and named column order are
    retained. This constructor does not sort, fill missing values, aggregate
    duplicates or coerce every numeric column to float. Those are separate
    operations, never implicit preparation policies.

    ``indexing='at'`` retains the full-scalar .at error-key encoding and boolean
    label rules as owned metadata. It requires complete, ungrouped keys.

    The normal Table contract requires unique leaf keys and nonempty unique
    string columns. Unsupported scalar values raise rather than silently lose
    their dtype/missing semantics. Public DataFrames are not modified.

    ``rows=True`` additionally owns pandas-style row scalar coercion for row()
    selection. Lookup-only tables omit this second matrix. Row coercion follows
    the selected columns, and row snapshots currently require ungrouped tables.
    ``report=True`` owns axes/dtypes/attrs for to_pandas() without row snapshots;
    rows=True includes report metadata. Plain lookup preparation owns neither.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError('table requires a pandas DataFrame')
    if indexing not in ('loc', 'at'):
        raise ValueError('indexing must be loc or at')
    if indexing == 'at' and groups:
        raise ValueError('at preparation requires complete keys')
    if (rows or report) and groups:
        raise ValueError('row/report preparation requires ungrouped tables')
    index_error = _at_index_spec(frame.index, encoded_errors=indexing == 'at') if not groups else None
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
                         [values for _, values in branch], selected, index_error)
        return Record({key: build(value, depth + 1) for key, value in branch.items()})
    result = build(root, 0)
    if not groups and (rows or report):
        # Row selection has a different scalar-coercion contract from column
        # lookup. Own it at preparation, rather than guessing a common dtype in
        # the financial kernel. Public axes and attrs are independent copies.
        row_values, row_dtypes, row_names = [], [], []
        if rows:
            for position in range(len(selected_frame)):
                public_row = selected_frame.iloc[position]
                row_values.append(tuple(freeze(public_row[name]) for name in selected))
                row_dtypes.append(public_row.dtype)
                row_names.append(public_row.name)
        object.__setattr__(result, '_metadata', (
            'frame', selected_frame.index.copy(deep=True),
            selected_frame.columns.copy(deep=True), tuple(selected_frame.dtypes),
            tuple(row_values) if rows else None, tuple(row_dtypes), deepcopy(selected_frame.attrs),
            selected_frame.flags.allows_duplicate_labels, tuple(row_names),
            (selected_frame.columns.dtype, selected_frame.columns.name)))
    return result


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


def record(row, *, preserve_scalar_types=False):
    """Prepare a Record from an explicitly selected public pandas Series.

    A model can keep its public model_point Cell unchanged and make a separate
    preparation Cell depend on that value. Its mixed-row coercion/name semantics
    stay in the public pandas selection; calculation reads the owned fields.
    """
    if not isinstance(row, pd.Series):
        raise TypeError('record requires a pandas Series')
    if not row.index.is_unique:
        raise ValueError('record fields must be unique')
    if preserve_scalar_types:
        # Series.items() can yield Python scalars while Series[key] returns a
        # numpy scalar. Preserve the actual public scalar-selection contract.
        return Record({key: freeze(row[key]) for key in row.index})
    return Record({key: _scalar(value) for key, value in row.items()})


def index(labels):
    """Own public Index labels for internal ordered traversal.

    The public Index Cell remains unchanged. Unique labels retain the existing
    Table representation with position data. Duplicate labels use an existing
    Record containing the owned key tuple, preserving order and multiplicity
    without weakening Table's unique-lookup-key invariant. This is a traversal
    input, not an implicit conversion of ambiguous labels into unique lookups.
    """
    if not isinstance(labels, pd.Index):
        raise TypeError('index requires a pandas Index')
    keys = tuple(_key(label) for label in labels)
    if not labels.is_unique:
        result = Record({'keys': keys})
        object.__setattr__(result, '_metadata', ('index',))
        return result
    return Table(keys,
                 tuple((position,) for position in range(len(labels))),
                 ('position',), _at_index_spec(labels, encoded_errors=False))



def _at_index_spec(index, *, encoded_errors=True):
    """Own only the metadata required for full-scalar pandas .at semantics."""
    multi = isinstance(index, pd.MultiIndex)
    levels = index.levels if multi else (index,)
    modes = []
    for level in levels:
        values = tuple(_key(value) for value in level)
        if values and all(type(value) is bool for value in values):
            modes.append(1)
        elif any(type(value) is bool for value in values):
            modes.append(0)
        else:
            modes.append(2)
    # Calibrate the installed pandas encoding at preparation, not in lookup.
    probe = pd.MultiIndex.from_tuples([('a', 0)])
    bias = int(probe._engine.values[0]) >> int(probe._engine.offsets[0])
    owned_levels = tuple(tuple(_key(value) for value in level) for level in levels)
    # Build level ownership at this explicit preparation boundary. Native
    # resource initialization must not call the Python Table constructor.
    level_tables = tuple(Table(level, [(0.0,)] * len(level), ('position',))
                         for level in owned_levels)
    return Record({
        'multi': multi, 'encoded_errors': encoded_errors,
        'levels': owned_levels, 'level_tables': level_tables,
        'offsets': tuple(map(int, index._engine.offsets)) if multi else (0,),
        'boolean_modes': tuple(modes), 'bias': bias})
