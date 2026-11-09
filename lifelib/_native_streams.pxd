from modelx_cython._float_sum_state cimport F64Sum
from modelx_cython._range_state cimport I64Range

cdef object omitted_argument

cdef class Stream:
    cdef object source, function, predicate, unpack, current, inner
    cdef bint closed, bounded, flattened, identity
    cdef int source_kind
    cdef Py_ssize_t position
    cdef I64Range counter
    cdef object next_value(self)
    cdef object next_flattened(self)
    cdef object next_input(self)

cdef object periods(object current_callable, tuple keywords, object start, object stop=*, object step=*)
cdef object over(object current_callable, tuple keywords, object source, object function, object where=*, object unpack=*)
cdef object flatten(object current_callable, tuple keywords, object sources)
cdef object sum_values(object current_callable, tuple keywords, object source)

cdef double sum_float_kernel(Stream source) except *
cdef object sum_float(object current_callable, tuple keywords, object source, object function=*, object where=*)
