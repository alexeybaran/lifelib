# cython: freethreading_compatible=True
"""Cython implementation of explicit immutable helpers, copied by mx2cy.

Only exact immutable Table/Record instances are specialized. Mutable inputs,
subclasses and replaced function References call the original supplied function.
Views belong to their Table and contain no formula or policy state.
"""
from array import array
from enum import IntEnum
import math
from libc.math cimport fabs, isfinite, floor
from libc.limits cimport LONG_MIN, LONG_MAX
from cpython.float cimport PyFloat_AS_DOUBLE, PyFloat_CheckExact
from cpython.long cimport PyLong_AsLong, PyLong_AsLongLongAndOverflow, PyLong_Check
from cpython.version cimport PY_VERSION_HEX
from cpython.ref cimport PyObject
cimport cython
from lifelib.immutable_inputs import Table, Record
from lifelib.typed_inputs import _FLOOR, _native_operations

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
cdef object _any_true = _native_operations['any_true']
cdef object _all_true = _native_operations['all_true']
cdef object _max_value = _native_operations['max_value']
cdef object _prepared_interpolation = _native_operations['prepared_interpolation']


cdef class TableView:
    cdef tuple keys, values, columns, ordered
    cdef dict positions, column_positions
    cdef long long[::1] integers
    cdef long long[::1] sorted_positions
    cdef object minimum, maximum
    cdef long long first_integer, last_integer
    cdef bint integral
    cdef bint numeric
    cdef bint contiguous
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
                self.first_integer = self.minimum
                self.last_integer = self.maximum
                # Table guarantees unique keys. Compute the span as Python ints.
                self.contiguous = self.maximum - self.minimum == len(self.ordered) - 1
                self.numeric = all(type(value) is float for row in self.values for value in row)
                if self.numeric:
                    self.width = len(self.columns)
                    self.numbers = array('d', [value for row in self.values for value in row])

    @cython.boundscheck(False)
    @cython.wraparound(False)
    cdef inline Py_ssize_t right(self, long long key) noexcept:
        cdef Py_ssize_t lo = 0, hi = self.integers.shape[0], mid
        if self.contiguous:
            if key < self.first_integer:
                return 0
            if key >= self.last_integer:
                return hi
            return <Py_ssize_t>(key - self.first_integer) + 1
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


cdef object any_true(object function, object values):
    return function(values)


cdef bint any_true_accepts(object function):
    return function is _any_true


cdef object all_true(object function, object values):
    return function(values)


cdef bint all_true_accepts(object function):
    return function is _all_true


cdef object max_value(object function, object values):
    return function(values)


cdef bint max_value_accepts(object function):
    return function is _max_value


cdef class LookupContext:
    def __reduce__(self):
        # Prepared resources are disposable and may contain memoryviews. Cell
        # results remain in their Space caches; rebuild resources on demand.
        return (LookupContext, ())

    def _mx_enable_private_lookup(self):
        # Called before the worker-exclusive collect receiver starts evaluating.
        self._private_owner = True

    cdef object get(self, object table, object column, Py_ssize_t* index):
        cdef TableView data
        cdef object retired_table, retired_data
        if self._private_owner:
            if table is self.first and column is self.column_first:
                index[0] = self.index_first
                return self.data_first
            if table is self.second and column is self.column_second:
                index[0] = self.index_second
                return self.data_second
        with cython.critical_section(self):
            if table is self.first and column is self.column_first:
                index[0] = self.index_first
                return self.data_first
            if table is self.second and column is self.column_second:
                index[0] = self.index_second
                return self.data_second
            if table is self.first:
                data = self.data_first
            elif table is self.second:
                data = self.data_second
            elif type(table) is Table:
                data = view(table)
            else:
                return None
            if data is not None and data.numeric:
                index[0] = numeric_column(data, column)
                if index[0] >= 0:
                    # Drop evicted references after the critical section.
                    retired_table, retired_data = self.second, self.data_second
                    self.second, self.data_second = self.first, self.data_first
                    self.column_second, self.index_second = self.column_first, self.index_first
                    self.first, self.data_first = table, data
                    self.column_first, self.index_first = column, index[0]
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


cdef object prepared_interpolation(object function, object table, object column, object years,
                                   object lookup_fn, object last_fn, object math_module):
    cdef TableView data
    cdef long long col, lower, upper
    cdef Py_ssize_t lo, hi
    cdef int overflow
    cdef double position, base, end
    if function is not _prepared_interpolation:
        return function(table, column, years, lookup_fn, last_fn, math_module)
    if (lookup_fn is not _lookup or last_fn is not _last_key
            or math_module is not math or math.floor is not _FLOOR
            or type(table) is not Table or not PyLong_Check(column) or not PyFloat_CheckExact(years)):
        return None
    position = PyFloat_AS_DOUBLE(years)
    if not -9223372036854775808.0 <= position < 9223372036854775808.0:
        return None
    col = PyLong_AsLongLongAndOverflow(column, &overflow)
    data = view(table)
    if overflow or not data.numeric or not 0 <= col < data.width:
        return None
    lower = <long long>floor(position)
    upper = data.maximum
    if lower >= upper:
        hi = data.sorted_positions[data.integers.shape[0] - 1]
        return data.numbers[hi * data.width + col]
    lo = data.right(lower) - 1
    if lo < 0 or data.integers[lo] != lower:
        return None
    hi = lo + 1
    if data.integers[hi] != lower + 1:
        return None
    base = data.numbers[data.sorted_positions[lo] * data.width + col]
    end = data.numbers[data.sorted_positions[hi] * data.width + col]
    return base + (end - base) * (position - lower)


cdef double lookup_f64(object function, LookupContext context, object table,
                       long long key, object column, object default=_missing) except? -1:
    cdef TableView data
    cdef Py_ssize_t index, col
    if function is _lookup:
        col = -1
        data = context.get(table, column, &col)
        if data is not None and data.numeric:
            index = data.right(key) - 1
            if index < 0 or data.integers[index] != key:
                if default is _missing:
                    raise KeyError(key)
                return default
            if index >= 0 and data.integers[index] == key:
                if col >= 0:
                    return data.numbers[data.sorted_positions[index] * data.width + col]
    return lookup(function, table, key, column) if default is _missing else lookup(function, table, key, column, default)


cdef double previous_f64(object function, LookupContext context, object table,
                         long long key, object column, object default=_missing) except? -1:
    cdef TableView data
    cdef Py_ssize_t index, col
    if function is _previous:
        col = -1
        data = context.get(table, column, &col)
        if data is not None and data.numeric:
            index = data.right(key) - 1
            if index < 0:
                if default is _missing:
                    raise ValueError(f'No key at or before {key!r}')
                return default
            if index >= 0:
                if col >= 0:
                    return data.numbers[data.sorted_positions[index] * data.width + col]
    return previous(function, table, key, column) if default is _missing else previous(function, table, key, column, default)


cdef inline double _lookup_clamped_f64(object function, LookupContext context, object table,
                                       long long key, object last_function, object column) except? -1:
    cdef TableView data = None
    cdef Py_ssize_t index, col
    cdef long long upper
    if function is _lookup and last_function is _last_key:
        col = -1
        if context is not None:
            data = context.get(table, column, &col)
        elif type(table) is Table:
            data = view(table)
        if data is not None and data.numeric:
            upper = data.last_integer
            if upper < key:
                key = upper
            index = data.right(key) - 1
            if index < 0 or data.integers[index] != key:
                raise KeyError(key)
            if context is None:
                col = numeric_column(data, column)
            if col >= 0:
                return data.numbers[data.sorted_positions[index] * data.width + col]
    return lookup(function, table, min(key, last_key(last_function, table)), column)


cdef double lookup_clamped_f64(object function, object table, long long key,
                               object last_function, object column) except? -1:
    return _lookup_clamped_f64(function, None, table, key, last_function, column)


cdef double lookup_clamped_context_f64(object function, LookupContext context, object table,
                                       long long key, object last_function, object column) except? -1:
    return _lookup_clamped_f64(function, context, table, key, last_function, column)


cdef bint bounded_lookup_f64(object function, object first_fn, object last_fn,
                             LookupContext context, object table, long long key,
                             str column, double below, double* value) except? -1:
    cdef TableView data
    cdef Py_ssize_t col = -1, row, count
    if function is not _lookup or first_fn is not _first_key or last_fn is not _last_key:
        return False
    data = context.get(table, column, &col)
    if data is None or col < 0:
        return False
    count = data.integers.shape[0]
    if not count:
        return False
    if context._private_owner and context.bounded_data is None:
        context.bounded_data = data
        context.bounded_column = col
    if key < data.integers[0]:
        value[0] = below
        return True
    if key >= data.integers[count - 1]:
        row = count - 1
    else:
        row = data.right(key) - 1
        if row < 0 or data.integers[row] != key:
            return False
    value[0] = data.numbers[data.sorted_positions[row] * data.width + col]
    return True


cdef int optional_lookup_f64(object contains_fn, object lookup_fn, object table,
                             long long key, object column, double* result) except? -1:
    """Return missing, found, or unsupported without invoking a replacement."""
    cdef TableView data
    cdef Py_ssize_t index, col
    if contains_fn is _contains and lookup_fn is _lookup and type(table) is Table:
        data = view(table)
        if data.numeric:
            index = data.right(key) - 1
            if index < 0 or data.integers[index] != key:
                return 0
            col = numeric_column(data, column)
            if col >= 0:
                result[0] = data.numbers[data.sorted_positions[index] * data.width + col]
                return 1
    return 2


cdef class GroupedView:
    cdef long long[::1] groups, keys, offsets
    cdef double[::1] values

    def __init__(self, groups, keys, offsets, values):
        self.groups = array('q', groups)
        self.keys = array('q', keys)
        self.offsets = array('q', offsets)
        self.values = array('d', values)


cdef object prepare_group(object record, str column):
    groups, keys, offsets, values = [], [], [0], []
    for group, table in record._items:
        kind = type(group)
        if kind is not int and not (
                type(kind) is type(IntEnum) and issubclass(kind, IntEnum)
                and kind.__eq__ is int.__eq__ and kind.__hash__ is int.__hash__
                and kind.__index__ is int.__index__):
            return None
        number = int.__index__(group)
        if not -(1 << 63) <= number < (1 << 63) or type(table) is not Table:
            return None
        if column not in table._columns or not all(
                type(key) is int and -(1 << 63) <= key < (1 << 63) for key in table._keys):
            return None
        col = table._columns.index(column)
        if not all(type(row[col]) is float for row in table._values):
            return None
        groups.append(number)
        for key, row in sorted(zip(table._keys, table._values)):
            keys.append(key)
            values.append(row[col])
        offsets.append(len(keys))
    return GroupedView(groups, keys, offsets, values)


cdef object group_view(object record, str column):
    cdef dict cache = record._native_groups
    prepared = cache.get(column, _missing)
    if prepared is _missing:
        prepared = cache.setdefault(column, prepare_group(record, column))
    return prepared


cdef Py_ssize_t group_slot(GroupedView data, long long group) except? -2:
    cdef Py_ssize_t i
    for i in range(data.groups.shape[0]):
        if data.groups[i] == group:
            return i
    return -1


cdef inline object probe_group(object prepared, long long group, Py_ssize_t* slot):
    slot[0] = -2
    if prepared is None:
        return None
    slot[0] = group_slot(<GroupedView>prepared, group)
    return prepared


cdef object group_probe(object has_fn, object record, long long group, str column,
                        Py_ssize_t* slot):
    if has_fn is not _has_group or type(record) is not Record:
        slot[0] = -2
        return None
    return probe_group(group_view(record, column), group, slot)


cdef object group_context_probe(LookupContext context, object has_fn, object record,
                                long long group, str column, Py_ssize_t* slot):
    # The compiler emits this only on the exact, unlocked Space path.
    # Keep the captured view alive across year evaluation and Reference changes.
    cdef tuple binding
    cdef object prepared
    if has_fn is not _has_group:
        slot[0] = -2
        return None
    binding = context.grouped
    if binding is not None and binding[0] is record and binding[1] is column:
        return probe_group(binding[2], group, slot)
    if type(record) is not Record:
        slot[0] = -2
        return None
    prepared = group_view(record, column)
    context.grouped = (record, column, prepared)
    return probe_group(prepared, group, slot)


cdef int group_data_value(GroupedView data, Py_ssize_t slot,
                           long long key, double* value) except -1:
    cdef Py_ssize_t lo, hi, mid
    lo, hi = data.offsets[slot], data.offsets[slot + 1]
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if key == data.keys[mid]:
            value[0] = data.values[mid]
            return 1
        if key < data.keys[mid]:
            hi = mid
        else:
            lo = mid + 1
    return 0


cdef int group_value(object sub_fn, object contains_fn, object lookup_fn, object prepared,
                     Py_ssize_t slot, long long key, double* value) except -1:
    if sub_fn is not _subtable or contains_fn is not _contains or lookup_fn is not _lookup:
        return 2
    return group_data_value(<GroupedView>prepared, slot, key, value)


cdef int group_context_value(LookupContext context, object sub_fn, object contains_fn,
    object lookup_fn, object prepared, Py_ssize_t slot, long long key, double* value) except -1:
    if sub_fn is not _subtable or contains_fn is not _contains or lookup_fn is not _lookup:
        return 2
    if (context._private_owner and context.group_data is None
            and context.grouped is not None and context.grouped[2] is prepared):
        context.group_data = prepared
    return group_data_value(<GroupedView>prepared, slot, key, value)


cdef bint bound_group_probe(LookupContext context, long long group, Py_ssize_t* slot) except? -1:
    cdef PyObject* data = <PyObject*>context.group_data
    if data == <PyObject*>None:
        return False
    slot[0] = group_slot(<GroupedView>data, group)
    return True


cdef int bound_group_value(LookupContext context, Py_ssize_t slot,
                           long long key, double* value) except -1:
    # Caller obtained this slot from the same admitted context before key evaluation.
    cdef PyObject* data = <PyObject*>context.group_data
    return group_data_value(<GroupedView>data, slot, key, value)


cdef bint f64_accepts(object function):
    return function is _sum_f64 and PY_VERSION_HEX >= 0x030c0000


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


cdef inline void remember_numeric_resource(LookupContext context, object source,
    object column, TableView data, Py_ssize_t index):
    if context._private_owner and data is not None and data.numeric and index >= 0:
        context.numeric_source = source
        context.numeric_column_source = column
        context.numeric_index = index
        context.numeric_data = data


cdef bint numeric_resource_ready(LookupContext context, const void* source, const void* column) noexcept:
    return (context._private_owner and context.numeric_data is not None
            and source == <const void*>context.numeric_source
            and (column == NULL or column == <const void*>context.numeric_column_source))


cdef inline double numeric_resource_value(LookupContext context, long long key, long long column,
    bint named, bint preceding, bint has_default, double default) except? -1:
    # The ready predicate proves lifetime/admission. Context retains the source
    # and immutable view; this borrowed pointer does not own another shared ref.
    cdef PyObject* data = <PyObject*>context.numeric_data
    cdef Py_ssize_t row = (<TableView>data).right(key) - 1
    cdef long long col
    if row < 0 or (not preceding and (<TableView>data).integers[row] != key):
        if has_default:
            return default
        if preceding:
            raise ValueError(f'No key at or before {key!r}')
        raise KeyError(key)
    col = context.numeric_index if named else column
    if not named and col < 0:
        col += (<TableView>data).width
    if col < 0 or col >= (<TableView>data).width:
        raise IndexError('tuple index out of range')
    return (<TableView>data).numbers[(<TableView>data).sorted_positions[row] * (<TableView>data).width + col]


cdef double bound_lookup_f64(LookupContext context, long long key, long long column,
                             bint named, bint has_default, double default) except? -1:
    return numeric_resource_value(context,key,column,named,False,has_default,default)


cdef double bound_previous_f64(LookupContext context, long long key, long long column,
                               bint named, bint has_default, double default) except? -1:
    return numeric_resource_value(context,key,column,named,True,has_default,default)

cdef bint bound_bounded_f64(LookupContext context, long long key,
                            double below, double* value) except? -1:
    # Context owns this immutable snapshot. No owning local view is needed.
    cdef PyObject* data = <PyObject*>context.bounded_data
    cdef Py_ssize_t row, count
    if data == <PyObject*>None:
        return False
    count = (<TableView>data).integers.shape[0]
    if key < (<TableView>data).integers[0]:
        value[0] = below
        return True
    if key >= (<TableView>data).integers[count - 1]:
        row = count - 1
    else:
        row = (<TableView>data).right(key) - 1
        if row < 0 or (<TableView>data).integers[row] != key:
            return False
    value[0] = (<TableView>data).numbers[
        (<TableView>data).sorted_positions[row] * (<TableView>data).width + context.bounded_column]
    return True



cdef double prepare_lookup_f64(object function, LookupContext context, object table,
    long long key, object column, object default=_missing) except? -1:
    cdef double value
    cdef TableView data
    cdef Py_ssize_t col = -1
    if context._private_owner:
        context.numeric_data = None
    value = lookup_f64(function,context,table,key,column,default)
    if context._private_owner and function is _lookup and type(table) is Table:
        data = context.get(table,column,&col)
        remember_numeric_resource(context,table,column,data,col)
    return value



cdef double prepare_previous_f64(object function, LookupContext context, object table,
    long long key, object column, object default=_missing) except? -1:
    cdef double value
    cdef TableView data
    cdef Py_ssize_t col = -1
    if context._private_owner:
        context.numeric_data = None
    value = previous_f64(function,context,table,key,column,default)
    if context._private_owner and function is _previous and type(table) is Table:
        data = context.get(table,column,&col)
        remember_numeric_resource(context,table,column,data,col)
    return value

# Preserve explicit conversion semantics, including replaced callables.
from builtins import float as _float_type

cdef double lookup_float_f64(object conversion, object function, LookupContext context,
                             object table, long long key, object column,
                             object default=_missing) except? -1:
    cdef TableView data
    cdef Py_ssize_t index, col = -1
    if conversion is _float_type and function is _lookup:
        data = context.get(table, column, &col)
        if data is not None and data.numeric:
            index = data.right(key) - 1
            if index < 0 or data.integers[index] != key:
                if default is _missing:
                    raise KeyError(key)
                # float(default) must parse strings, unlike implicit C conversion.
                return conversion(default)
            if col >= 0:
                return data.numbers[data.sorted_positions[index] * data.width + col]
    if default is _missing:
        return conversion(function(table, key, column))
    return conversion(function(table, key, column, default))
