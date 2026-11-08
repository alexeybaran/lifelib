# cython: freethreading_compatible=True
"""Native input-order integer key spans; no policy state or alternate tables."""
from array import array
import cython
from libc.math cimport isfinite
from lifelib.immutable_inputs import Table
from lifelib.table_keys import keys as _keys


cdef class KeySpan:
    pass


cdef object keys(object function, object table):
    if function is _keys and type(table) is Table:
        return table._keys
    return function(table)


cdef KeySpan keys_span(object function, object table):
    cdef KeySpan span
    if function is not _keys or type(table) is not Table:
        return None
    span = table._native_cache.get(KeySpan)
    if span is not None:
        return span
    values = table._keys
    if not all(type(key) is int and -(1 << 63) <= key < (1 << 63) for key in values):
        return None
    span = KeySpan()
    span.owner = table
    span.values = array('q', values)
    table._native_cache[KeySpan] = span
    return span


cdef Py_ssize_t key_span_count(KeySpan span) noexcept:
    return span.values.shape[0]


@cython.boundscheck(False)
@cython.wraparound(False)
cdef long long key_span_at(KeySpan span, Py_ssize_t position) except? -1:
    cdef Py_ssize_t size = span.values.shape[0]
    if position < 0:
        position += size
    if position < 0 or position >= size:
        raise IndexError('tuple index out of range')
    return span.values[position]


cdef class FloatKeySpan:
    pass


cdef FloatKeySpan keys_float_span(object function, object table):
    cdef FloatKeySpan span
    if function is not _keys or type(table) is not Table:
        return None
    span = table._native_cache.get(FloatKeySpan)
    if span is not None:
        return span
    values = table._keys
    for key in values:
        if type(key) is not float or not isfinite(key):
            return None
    span = FloatKeySpan()
    span.owner = table
    span.values = array('d', values)
    table._native_cache[FloatKeySpan] = span
    return span


cdef Py_ssize_t float_key_span_count(FloatKeySpan span) noexcept:
    return span.values.shape[0]


@cython.boundscheck(False)
@cython.wraparound(False)
cdef double float_key_span_at(FloatKeySpan span, Py_ssize_t position) except? -1:
    cdef Py_ssize_t size = span.values.shape[0]
    if position < 0:
        position += size
    if position < 0 or position >= size:
        raise IndexError('tuple index out of range')
    return span.values[position]
