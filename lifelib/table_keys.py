"""Ordered key traversal over the existing owned table representation."""


def keys(table):
    """Return keys in input order, preserving the existing sequence identity.

    Immutable Table keys can use a native int64 span in compiled iterations.
    Other representations retain the supplied function's ordinary semantics.
    """
    return table['keys']


keys.__modelx_native_operation__ = 'keys'
keys.__modelx_cython_helper__ = ('lifelib._native_indices', 'keys')
keys.__modelx_cython_iteration__ = (
    'keys_span', 'KeySpan', 'key_span_count', 'key_span_at')
keys.__modelx_cython_iteration_f64__ = (
    'keys_float_span', 'FloatKeySpan', 'float_key_span_count', 'float_key_span_at')
