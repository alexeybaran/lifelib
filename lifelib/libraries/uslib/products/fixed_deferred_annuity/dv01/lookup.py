"""Keyed table operations used by the DV01 model."""

from enum import IntEnum


def _normalize_key(table, key):
    """Translate typed enum keys back to ordinary pandas labels when necessary."""
    if isinstance(key, tuple):
        values = []
        for level, value in enumerate(key):
            if isinstance(value, IntEnum):
                labels = table.index.get_level_values(level)
                if value.name in labels:
                    value = value.name
                elif value.name.lower() in labels:
                    value = value.name.lower()
            values.append(value)
        return tuple(values)
    if isinstance(key, IntEnum):
        labels = table.index
        if key.name in labels:
            return key.name
        if key.name.lower() in labels:
            return key.name.lower()
    return key

def field(table, key, column):
    return table.loc[_normalize_key(table, key), column]

def at(table, key, column):
    return float(table.loc[_normalize_key(table, key), column])

def get(table, key, column, default=0.0):
    key = _normalize_key(table, key)
    return float(table.loc[key, column]) if key in table.index else float(default)

def linear(table, key, column):
    """Linear interpolation on an ungrouped numeric index; hold above range."""
    if len(table.index) == 0:
        raise KeyError(key)
    lo = [x for x in table.index if x <= key]
    if not lo:
        raise KeyError(key)
    a = max(lo)
    if a == table.index.max():
        return float(table.loc[a, column])
    hi = min(x for x in table.index if x > key)
    y0, y1 = float(table.loc[a, column]), float(table.loc[hi, column])
    return y0 + (y1-y0) * (key-a) / (hi-a)
