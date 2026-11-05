# cython: freethreading_compatible=True
"""Cython implementation of explicit immutable helpers, copied by mx2cy.

Only exact immutable Table/Record instances are specialized. Mutable inputs,
subclasses and replaced function References call the original supplied function.
Views belong to their Table and contain no formula or policy state.
"""
from array import array
from enum import IntEnum
from libc.math cimport fabs, isfinite
from libc.limits cimport LONG_MIN, LONG_MAX
from cpython.long cimport PyLong_AsLong
from cpython.version cimport PY_VERSION_HEX
cimport cython
from lifelib.immutable_inputs import Table, Record
from lifelib.typed_inputs import _native_operations

cdef object _missing = object()
cdef object _lookup = _native_operations['lookup']
cdef object _previous = _native_operations['previous']
cdef object _contains = _native_operations['contains']
cdef object _key_count = _native_operations['key_count']
cdef object _key_at = _native_operations['key_at']
cdef object _first_key = _native_operations['first_key']
cdef object _last_key = _native_operations['last_key']
cdef object _subtable = _native_operations['subtable']
cdef object _has_group = _native_operations['has_group']
cdef object _sum_f64 = _native_operations['sum_f64']
cdef object _sum_helper = _native_operations['sum_helper']


cdef class TableView:
    cdef tuple keys, values, columns, ordered
    cdef dict positions, column_positions
    cdef long long[::1] integers
    cdef long long[::1] sorted_positions
    cdef object minimum, maximum
    cdef bint integral
    cdef bint numeric
    cdef Py_ssize_t width
    cdef double[::1] numbers

    def __init__(self, table):
        self.keys = table['keys']
        self.values = table['values']
        self.columns = table['columns']
        self.positions = dict(zip(self.keys, range(len(self.keys))))
        self.column_positions = dict(zip(self.columns, range(len(self.columns))))
        self.ordered = table._ordered
        if self.ordered:
            self.minimum, self.maximum = min(self.keys), max(self.keys)
            self.integral = all(type(key) is int and -(1 << 63) <= key < (1 << 63)
                                for key in self.keys)
            if self.integral:
                self.integers = array('q', self.ordered)
                self.sorted_positions = array('q', [self.positions[key] for key in self.ordered])
                self.numeric = all(type(value) is float for row in self.values for value in row)
                if self.numeric:
                    self.width = len(self.columns)
                    self.numbers = array('d', [value for row in self.values for value in row])

    cdef Py_ssize_t right(self, long long key) noexcept:
        cdef Py_ssize_t lo = 0, hi = self.integers.shape[0], mid
        while lo < hi:
            mid = lo + (hi - lo) // 2
            if key < self.integers[mid]:
                hi = mid
            else:
                lo = mid + 1
        return lo

    cdef object value(self, Py_ssize_t row, object column):
        cdef Py_ssize_t col
        if type(column) is str:
            found = self.column_positions.get(column)
            if found is None:
                # Preserve tuple.index's exception, including its message.
                col = self.columns.index(column)
            else:
                col = found
            return self.values[row][col]
        if isinstance(column, str):
            return self.values[row][self.columns.index(column)]
        return self.values[row][column]


cdef TableView view(object table):
    cdef dict cache = table._native_cache
    result = cache.get(TableView)
    if result is None:
        result = cache.setdefault(TableView, TableView(table))
    return <TableView>result


cdef object lookup(object function, object table, object key, object column, object default=_missing):
    cdef TableView data
    if (function is _lookup and type(table) is Table
            and (type(column) in (str, int) or isinstance(column, IntEnum))):
        data = view(table)
        position = data.positions.get(key)
        if position is not None:
            return data.value(position, column)
        if default is not _missing:
            return default
        raise KeyError(key)
    return function(table, key, column) if default is _missing else function(table, key, column, default)


cdef object previous(object function, object table, object key, object column, object default=_missing):
    cdef TableView data
    cdef Py_ssize_t index
    if function is _previous and type(table) is Table:
        data = view(table)
        if data.integral and type(key) is int and -(1 << 63) <= key < (1 << 63):
            index = data.right(key) - 1
            if index >= 0:
                return data.value(data.sorted_positions[index], column)
            if default is not _missing:
                return default
            raise ValueError(f'No key at or before {key!r}')
    return function(table, key, column) if default is _missing else function(table, key, column, default)


cdef object contains(object function, object table, object key):
    if function is _contains and type(table) is Table:
        return key in view(table).positions
    return function(table, key)


cdef object key_count(object function, object table):
    if function is _key_count and type(table) is Table:
        return len(view(table).keys)
    return function(table)


cdef object key_at(object function, object table, object index):
    if function is _key_at and type(table) is Table:
        if index < 0:
            raise IndexError(index)
        return view(table).keys[index]
    return function(table, index)


cdef object first_key(object function, object table):
    cdef TableView data
    if function is _first_key and type(table) is Table:
        data = view(table)
        if data.ordered:
            return data.minimum
    return function(table)


cdef object last_key(object function, object table):
    cdef TableView data
    if function is _last_key and type(table) is Table:
        data = view(table)
        if data.ordered:
            return data.maximum
    return function(table)


cdef object subtable(object function, object table, object key):
    if function is _subtable and type(table) is Record:
        return table._index[key]
    return function(table, key)


cdef object has_group(object function, object table, object key):
    if function is _has_group and type(table) is Record:
        return key in table._index
    return function(table, key)


cdef object sum_f64(object function, object values):
    if function is _sum_f64:
        return sum(values, 0.0)
    return function(values)


cdef class LookupContext:
    cdef object get(self, object table):
        with cython.critical_section(self):
            if table is self.first:
                return self.data_first
            if table is self.second:
                return self.data_second
            if type(table) is not Table:
                return None
            data = view(table)
            self.second, self.data_second = self.first, self.data_first
            self.first, self.data_first = table, data
            return data


cdef Py_ssize_t numeric_column(TableView data, object column) except? -1:
    cdef Py_ssize_t index
    if type(column) is str:
        found = data.column_positions.get(column)
        if found is None:
            return -1
        return found
    if type(column) is int and -data.width <= column < data.width:
        index = column
        return index if index >= 0 else data.width + index
    return -1


cdef double lookup_f64(object function, LookupContext context, object table,
                       long long key, object column, object default=_missing) except? -1:
    cdef TableView data
    cdef Py_ssize_t index, col
    if function is _lookup:
        data = context.get(table)
        if data is not None and data.numeric:
            index = data.right(key) - 1
            if index < 0 or data.integers[index] != key:
                if default is _missing:
                    raise KeyError(key)
                return default
            if index >= 0 and data.integers[index] == key:
                col = numeric_column(data, column)
                if col >= 0:
                    return data.numbers[data.sorted_positions[index] * data.width + col]
    return lookup(function, table, key, column) if default is _missing else lookup(function, table, key, column, default)


cdef double previous_f64(object function, LookupContext context, object table,
                         long long key, object column, object default=_missing) except? -1:
    cdef TableView data
    cdef Py_ssize_t index, col
    if function is _previous:
        data = context.get(table)
        if data is not None and data.numeric:
            index = data.right(key) - 1
            if index < 0:
                if default is _missing:
                    raise ValueError(f'No key at or before {key!r}')
                return default
            if index >= 0:
                col = numeric_column(data, column)
                if col >= 0:
                    return data.numbers[data.sorted_positions[index] * data.width + col]
    return previous(function, table, key, column) if default is _missing else previous(function, table, key, column, default)


cdef bint f64_accepts(object function):
    return function is _sum_f64 and PY_VERSION_HEX >= 0x030c0000


cdef void f64_init(F64Sum* state) noexcept:
    state.total = 0.0
    state.correction = 0.0


cdef void f64_add(F64Sum* state, double value) noexcept:
    cdef double following = state.total + value
    if fabs(state.total) >= fabs(value):
        state.correction += (state.total - following) + value
    else:
        state.correction += (value - following) + state.total
    state.total = following


cdef double f64_result(F64Sum* state) noexcept:
    if state.correction != 0.0 and isfinite(state.correction):
        return state.total + state.correction
    return state.total


cdef object sum_helper(object function, object values):
    cdef double total = 0.0, correction = 0.0, value, following
    if function is not _sum_helper:
        return function(values)
    # This test implementation qualifies the 3.13 float-start sum contract.
    # Other interpreter versions retain their own builtin's behavior.
    if PY_VERSION_HEX >> 16 != 0x030d:
        return sum(values, 0.0)
    iterator = iter(values)
    for item in iterator:
        if type(item) is float:
            value = item
            following = total + value
            if fabs(total) >= fabs(value):
                correction += (total - following) + value
            else:
                correction += (value - following) + total
            total = following
        elif isinstance(item, int) and LONG_MIN <= item <= LONG_MAX:
            total += <double>PyLong_AsLong(item)
        else:
            if correction != 0.0 and isfinite(correction):
                total += correction
            result = total + item
            for item in iterator:
                result = result + item
            return result
    if correction != 0.0 and isfinite(correction):
        total += correction
    return total
