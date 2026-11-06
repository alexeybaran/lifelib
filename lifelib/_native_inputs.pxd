from libc.math cimport fabs, isfinite

cdef object lookup(object function, object table, object key, object column, object default=*)
cdef object previous(object function, object table, object key, object column, object default=*)
cdef object contains(object function, object table, object key)
cdef object key_count(object function, object table)
cdef object key_at(object function, object table, object index)
cdef object first_key(object function, object table)
cdef object last_key(object function, object table)
cdef object subtable(object function, object table, object key)
cdef object has_group(object function, object table, object key)
cdef object sum_f64(object function, object values)
cdef object sum_helper(object function, object values)
cdef object any_true(object function, object values)
cdef bint any_true_accepts(object function)
cdef object all_true(object function, object values)
cdef bint all_true_accepts(object function)
cdef object max_value(object function, object values)
cdef bint max_value_accepts(object function)

cdef inline double f64_abs(double value) noexcept nogil:
    return fabs(value)

cdef object prepared_interpolation(object function, object table, object column, object years,
                                   object lookup_fn, object last_fn, object math_module)

cdef struct F64Sum:
    double total
    double correction
cdef bint f64_accepts(object function)
cdef inline void f64_init(F64Sum* state) noexcept:
    state.total = 0.0
    state.correction = 0.0


cdef inline void f64_add(F64Sum* state, double value) noexcept:
    cdef double following = state.total + value
    if fabs(state.total) >= fabs(value):
        state.correction += (state.total - following) + value
    else:
        state.correction += (value - following) + state.total
    state.total = following


cdef inline double f64_result(F64Sum* state) noexcept:
    if state.correction != 0.0 and isfinite(state.correction):
        return state.total + state.correction
    return state.total


cdef class LookupContext:
    cdef object first, second
    cdef object data_first, data_second
    cdef object column_first, column_second
    cdef Py_ssize_t index_first, index_second
    cdef tuple grouped
    cdef object get(self, object table, object column, Py_ssize_t* index)
cdef double lookup_f64(object function, LookupContext context, object table,
                       long long key, object column, object default=*) except? -1
cdef double previous_f64(object function, LookupContext context, object table,
                         long long key, object column, object default=*) except? -1
cdef double lookup_clamped_f64(object function, object table, long long key,
                               object last_function, object column) except? -1
cdef double lookup_clamped_context_f64(object function, LookupContext context, object table,
                                       long long key, object last_function, object column) except? -1
cdef bint bounded_lookup_f64(object function, object first_fn, object last_fn,
                             LookupContext context, object table, long long key,
                             str column, double below, double* value) except? -1
cdef int optional_lookup_f64(object contains_fn, object lookup_fn, object table,
                             long long key, object column, double* result) except? -1
cdef object group_probe(object has_fn, object record, long long group, str column,
                        Py_ssize_t* slot)
cdef object group_context_probe(LookupContext context, object has_fn, object record,
                                long long group, str column, Py_ssize_t* slot)
cdef int group_value(object sub_fn, object contains_fn, object lookup_fn, object prepared,
                     Py_ssize_t slot, long long key, double* value) except -1
