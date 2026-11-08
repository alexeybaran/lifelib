cdef class KeySpan:
    cdef object owner
    cdef long long[::1] values

cdef object keys(object function, object table)
cdef KeySpan keys_span(object function, object table)
cdef Py_ssize_t key_span_count(KeySpan span) noexcept
cdef long long key_span_at(KeySpan span, Py_ssize_t position) except? -1
