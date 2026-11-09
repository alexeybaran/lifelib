"""Ordered key traversal over the existing owned table representation."""


def keys(table):
    """Return keys in input order, preserving the existing sequence identity.

    Owned Table keys and Record key tuples can use native integer/float/string
    spans in compiled iterations, preserving duplicate labels and source order.
    Other representations retain the supplied function's ordinary semantics.
    """
    return table['keys']


keys.__modelx_native_operation__ = 'keys'
keys.__modelx_cython_helper__ = ('lifelib._native_indices', 'keys')
keys.__modelx_cython_call_layout__ = 'keywords'
keys.__modelx_cython_scalar_result__ = 'object'
keys.__modelx_cython_iteration__ = (
    'keys_span', 'KeySpan', 'key_span_count', 'key_span_at')
keys.__modelx_cython_iteration_f64__ = (
    'keys_float_span', 'FloatKeySpan', 'float_key_span_count', 'float_key_span_at')
keys.__modelx_cython_iteration_str__ = (
    'keys_str_span', 'StrKeySpan', 'str_key_span_count', 'str_key_span_at')
