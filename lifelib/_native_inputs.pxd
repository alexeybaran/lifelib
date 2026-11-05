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

cdef struct F64Sum:
    double total
    double correction
cdef bint f64_accepts(object function)
cdef void f64_init(F64Sum* state) noexcept
cdef void f64_add(F64Sum* state, double value) noexcept
cdef double f64_result(F64Sum* state) noexcept

cdef class LookupContext:
    cdef object first, second
    cdef object data_first, data_second
    cdef object get(self, object table)
cdef double lookup_f64(object function, LookupContext context, object table,
                       long long key, object column, object default=*) except? -1
cdef double previous_f64(object function, LookupContext context, object table,
                         long long key, object column, object default=*) except? -1
