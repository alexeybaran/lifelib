"""Differential contracts for the explicitly prepared scalar lookup boundary."""
import importlib
import math
from pathlib import Path
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from lifelib import pandas_inputs as h


@pytest.fixture(scope='module')
def compiled_provider(tmp_path_factory):
    root = tmp_path_factory.mktemp('native-pandas')
    provider = Path(h.__file__).with_name('_native_pandas.pyx')
    (root / 'probe.pyx').write_text(provider.read_text() + '''

def invoke(function, table, key, column):
    return lookup(function, table, key, column)

def invoke_double(function, table, key, column):
    return lookup_f64(function, None, table, key, column)
''')
    (root / 'setup.py').write_text('''from setuptools import setup
from Cython.Build import cythonize
setup(ext_modules=cythonize('probe.pyx', compiler_directives={'language_level': 3}))
''')
    run = subprocess.run([sys.executable, 'setup.py', 'build_ext', '--inplace'],
                         cwd=root, capture_output=True, text=True)
    (root / 'build.log').write_text(run.stdout + run.stderr)
    assert run.returncode == 0, run.stdout + run.stderr
    sys.path.insert(0, str(root))
    try:
        yield importlib.import_module('probe')
    finally:
        sys.path.remove(str(root))
        sys.modules.pop('probe', None)


@pytest.fixture(params=['invoke', 'invoke_double'])
def native(compiled_provider, request):
    return getattr(compiled_provider, request.param)


def outcome(function):
    try:
        value = function()
        return ('value', 'nan' if math.isnan(value) else value)
    except Exception as error:
        return ('exception', type(error), error.args)


@pytest.mark.parametrize('frame,key,column', [
    (pd.DataFrame({'rate': [0.1, 0.2]}, index=[8, 2]), 2, 'rate'),
    (pd.DataFrame({'rate': [0.1]}, index=['M']), 'M', 'rate'),
    (pd.DataFrame({'rate': [0.1]}, index=pd.MultiIndex.from_tuples([('M', 42)])), ('M', 42), 'rate'),
    (pd.DataFrame({'rate': [float('nan'), -0.0]}, index=[0, 1]), 0, 'rate'),
    (pd.DataFrame({'rate': [float('inf')]}, index=[0]), 0, 'rate'),
    (pd.DataFrame({'rate': []}), 0, 'rate'),
    (pd.DataFrame({'rate': [1.0]}, index=[1]), 0, 'rate'),
    (pd.DataFrame({'rate': [1.0]}, index=[1]), 1, 'absent'),
    (pd.DataFrame({'rate': [1.0, 2.0]}, index=[1, 1]), 1, 'rate'),
    (pd.DataFrame([[1.0, 2.0]], columns=['rate', 'rate']), 0, 'rate'),
    (pd.DataFrame({'rate': pd.Series([pd.NA], dtype='Float64')}), 0, 'rate'),
    (pd.DataFrame({'rate': pd.Series([3], dtype='int64')}), 0, 'rate'),
    (pd.DataFrame({'rate': ['0.3']}), 0, 'rate'),
    (pd.DataFrame({'rate': [None]}), 0, 'rate'),
    (pd.DataFrame({'rate': [2.0]}, index=[True]), 1, 'rate'),
    (pd.DataFrame({'rate': [2.0]}, index=[1.0]), 1, 'rate'),
    (pd.DataFrame({'rate': [2.0]}, index=[1]), np.int64(1), 'rate'),
    (pd.DataFrame({'rate': [1.0, 2.0]}, index=pd.MultiIndex.from_tuples([('M', 41), ('M', 42)])), 'M', 'rate'),
])
def test_native_matches_pandas(native, frame, key, column):
    table = h.numeric_table(frame)
    expected = outcome(lambda: float(frame.loc[key, column]))
    assert outcome(lambda: h.lookup(table, key, column)) == expected
    assert outcome(lambda: native(h.lookup, table, key, column)) == expected
    restored = pickle.loads(pickle.dumps(table))
    assert outcome(lambda: native(h.lookup, restored, key, column)) == expected


def test_explicit_snapshot_lifetime_and_signed_zero(native):
    frame = pd.DataFrame({'rate': [-0.0]}, index=[2])
    table = h.numeric_table(frame)
    frame.loc[2, 'rate'] = 5.0
    assert math.copysign(1.0, native(h.lookup, table, 2, 'rate')) == -1.0
    assert native(h.lookup, h.numeric_table(frame), 2, 'rate') == 5.0


def test_callable_override_identity_and_exception(native):
    table = h.numeric_table(pd.DataFrame({'rate': [1.0]}))
    calls = []
    failure = LookupError('sentinel')
    def replacement(*args):
        calls.append(args)
        raise failure
    with pytest.raises(LookupError) as caught:
        native(replacement, table, 0, 'rate')
    assert caught.value is failure
    assert calls == [(table, 0, 'rate')]


def test_native_load_does_not_call_pandas_indexer(native, monkeypatch):
    frame = pd.DataFrame({'rate': [1.5]}, index=[4])
    table = h.numeric_table(frame)
    def forbidden(_):
        raise AssertionError('pandas indexing reached')
    monkeypatch.setattr(pd.DataFrame, 'loc', property(forbidden))
    assert native(h.lookup, table, 4, 'rate') == 1.5
    with pytest.raises(AssertionError, match='pandas indexing'):
        h.lookup(table, 4, 'rate')


def test_mixed_columns_and_numeric_conversion_boundaries(native):
    frame = pd.DataFrame({'label': ['M', 'F'],
                          'rate': [0.1, 0.2],
                          'integer': np.array([2**63 - 1, -(2**63)], dtype=np.int64),
                          'unsigned': np.array([2**64 - 1, 2**53 + 1], dtype=np.uint64),
                          'boolean': [True, False],
                          'single': np.array([0.1, -0.0], dtype=np.float32)})
    table = h.numeric_table(frame)
    for column in frame.columns:
        for key in frame.index:
            assert outcome(lambda: native(h.lookup, table, key, column)) == outcome(
                lambda: float(frame.loc[key, column]))


def test_float_callable_replacement_is_observed(native, monkeypatch):
    import builtins
    table = h.numeric_table(pd.DataFrame({'rate': [1.0]}))
    calls = []
    def replacement(value):
        calls.append(value)
        return 7.0
    with monkeypatch.context() as patch:
        patch.setattr(builtins, 'float', replacement)
        result = native(h.lookup, table, 0, 'rate')
    assert result == 7.0
    assert calls == [1.0]
