"""Native scalar loads for explicitly owned numeric snapshots."""
import builtins as _builtins
from lifelib.pandas_inputs import NumericTable, lookup as _lookup, _plain_key
_FLOAT = _builtins.float


cdef class LookupContext:
    def __reduce__(self):
        return (LookupContext, ())


cdef bint _ready(object function, object table, object key, object column) except -1:
    return (function is _lookup and _builtins.float is _FLOAT
            and type(table) is NumericTable and table._native_ready
            and _plain_key(key) and type(column) is str
            and key in table._keys and column in table._columns)


cdef double _value(object table, object key, object column) except? -1:
    cdef const double[:, ::1] values = table._values
    cdef Py_ssize_t row = table._keys[key]
    cdef Py_ssize_t col = table._columns[column]
    return values[row, col]


cdef object lookup(object function, object table, object key, object column):
    if _ready(function, table, key, column):
        return _value(table, key, column)
    # Missing labels use pandas itself to preserve exception value/shape/order.
    return function(table, key, column)


cdef double lookup_f64(object function, LookupContext context, object table,
                        object key, object column) except? -1:
    if _ready(function, table, key, column):
        return _value(table, key, column)
    return function(table, key, column)
