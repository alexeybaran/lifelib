cdef class LookupContext:
    pass

cdef object lookup(object function, object table, object key, object column)
cdef double lookup_f64(object function, LookupContext context, object table,
                        object key, object column) except? -1
