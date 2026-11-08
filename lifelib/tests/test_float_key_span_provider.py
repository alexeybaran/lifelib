"""Float producer ABI, tested directly without generator/compiler recognition."""
import importlib
from pathlib import Path
import pickle
import subprocess
import sys

import lifelib
import pandas as pd
import pytest
from lifelib import pandas_inputs
from lifelib.immutable_inputs import Table
from lifelib.table_keys import keys


@pytest.fixture(scope='module')
def native(tmp_path_factory):
    root = tmp_path_factory.mktemp('float-key-span')
    provider = Path(lifelib.__file__).parent
    for suffix in ['pyx', 'pxd']:
        (root / ('indices.' + suffix)).write_bytes((provider / ('_native_indices.' + suffix)).read_bytes())
    (root / 'span_probe.pyx').write_text('''cimport indices
def read(function, table):
    cdef indices.FloatKeySpan span = indices.keys_float_span(function, table)
    if span is None:
        return None
    return [indices.float_key_span_at(span, i) for i in range(indices.float_key_span_count(span))]
def at(function, table, Py_ssize_t position):
    cdef indices.FloatKeySpan span = indices.keys_float_span(function, table)
    if span is None:
        raise TypeError('not admitted')
    return indices.float_key_span_at(span, position)
''')
    (root / 'setup.py').write_text("from setuptools import setup\nfrom Cython.Build import cythonize\nsetup(ext_modules=cythonize(['indices.pyx','span_probe.pyx'],compiler_directives={'language_level':3}))\n")
    run = subprocess.run([sys.executable, 'setup.py', 'build_ext', '--inplace'], cwd=root,
                         capture_output=True, text=True)
    (root / 'build.log').write_text(run.stdout + run.stderr)
    assert run.returncode == 0, run.stdout + run.stderr
    sys.path.insert(0, str(root))
    try:
        yield importlib.import_module('span_probe')
    finally:
        sys.path.remove(str(root))
        sys.modules.pop('span_probe', None)
        sys.modules.pop('indices', None)


@pytest.mark.parametrize('labels', [(), (35.5, 20.0, -0.0), (float(2**63), 1.5)])
def test_order_empty_pickle_and_bounds(native, labels):
    table = pandas_inputs.index(pd.Index(labels, dtype=float))
    assert keys(table) == labels
    for source in [table, pickle.loads(pickle.dumps(table))]:
        assert native.read(keys, source) == list(labels)
        if labels:
            assert native.at(keys, source, -1) == labels[-1]
        for position in [len(labels), -len(labels)-1]:
            with pytest.raises(IndexError, match='tuple index out of range'):
                native.at(keys, source, position)


@pytest.mark.parametrize('labels', [(1, 2), (True, False), ('a', 'b'), (1.0, float('inf')), (float('nan'),)])
def test_admission_declines_without_changing_key_types(native, labels):
    table = Table(labels, [(1.0,)] * len(labels), ('rate',))
    assert native.read(keys, table) is None


def test_current_function_is_not_invoked_by_admission(native):
    events = []
    def replacement(table):
        events.append(table)
        return (7.5,)
    table = pandas_inputs.index(pd.Index([35.5, 20.5]))
    assert native.read(replacement, table) is None
    assert events == []


def test_public_index_ownership_and_errors():
    public = pd.Index(['equity', 'bond'], name='fund')
    table = pandas_inputs.index(public)
    assert public.name == 'fund' and type(public) is pd.Index
    assert keys(table) == ('equity', 'bond')
    assert table.lookup('bond', 'position') == 1
    with pytest.raises(ValueError, match='unique'):
        pandas_inputs.index(pd.Index(['fund', 'fund']))
    with pytest.raises(TypeError, match='pandas Index'):
        pandas_inputs.index(['fund'])
