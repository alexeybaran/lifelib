"""Live contract and primitive Cython producer for ordered owned-table keys."""
import importlib
from pathlib import Path
import pickle
import subprocess
import sys

import lifelib
import pytest
from lifelib.immutable_inputs import Table
from lifelib.table_keys import keys


@pytest.fixture(scope='module')
def native(tmp_path_factory):
    root=tmp_path_factory.mktemp('native-indices')
    provider=Path(lifelib.__file__).parent
    for suffix in ('.pyx','.pxd'):
        (root/('indices'+suffix)).write_bytes((provider/('_native_indices'+suffix)).read_bytes())
    (root/'probe.pyx').write_text('''cimport indices

def collect(function, table):
    cdef indices.KeySpan span = indices.keys_span(function, table)
    cdef Py_ssize_t i
    if span is None: return None
    return [indices.key_span_at(span, i) for i in range(indices.key_span_count(span))]

def at(function, table, Py_ssize_t position):
    cdef indices.KeySpan span = indices.keys_span(function, table)
    return indices.key_span_at(span, position)

def total(function, table):
    cdef indices.KeySpan span = indices.keys_span(function, table)
    cdef Py_ssize_t i, n = indices.key_span_count(span)
    cdef long long value = 0
    for i in range(n):
        value += indices.key_span_at(span, i)
    return value
''')
    (root/'setup.py').write_text("from setuptools import setup\nfrom Cython.Build import cythonize\nsetup(ext_modules=cythonize(['indices.pyx','probe.pyx'],compiler_directives={'language_level':3,'freethreading_compatible':True}))\n")
    run=subprocess.run([sys.executable,'setup.py','build_ext','--inplace'],cwd=root,capture_output=True,text=True)
    (root/'build.log').write_text(run.stdout+run.stderr)
    assert run.returncode==0,run.stdout+run.stderr
    sys.path.insert(0,str(root))
    try:yield importlib.import_module('probe')
    finally:
        sys.path.remove(str(root));sys.modules.pop('probe',None);sys.modules.pop('indices',None)


@pytest.mark.parametrize('values', [(9,-3,5), (), (-(1<<63),(1<<63)-1)])
def test_order_empty_width_bounds_and_pickle(native,values):
    table=Table(values,[(1.0,)]*len(values),('rate',))
    assert keys(table) is table['keys']
    assert native.collect(keys,table)==list(values)
    assert native.collect(keys,pickle.loads(pickle.dumps(table)))==list(values)
    if values: assert native.at(keys,table,-1)==values[-1]
    with pytest.raises(IndexError,match='tuple index out of range'):native.at(keys,table,len(values))


@pytest.mark.parametrize('values', [(True,), (1.0,), ('M',), (1<<63,)])
def test_other_domains_keep_original_sequence(native,values):
    table=Table(values,[(1.0,)],('rate',))
    assert keys(table)==values
    assert native.collect(keys,table) is None


def test_no_python_keys_or_iterator_in_native_scan(native):
    table=Table((9,-3,5),[(1.0,)]*3,('rate',));calls=[]
    def profile(frame,event,arg):
        if event=='call' and frame.f_code is keys.__code__:calls.append('keys')
    sys.setprofile(profile)
    try:assert native.total(keys,table)==11
    finally:sys.setprofile(None)
    assert calls==[]


def test_replacement_probe_never_evaluates_replacement(native):
    table=Table((1,),((1.0,),),('rate',))
    def replacement(table):raise AssertionError('admission evaluated current callable')
    assert native.collect(replacement,table) is None
    raw={'keys':[9,2]}
    assert keys(raw) is raw['keys']
