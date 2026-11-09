"""Model adaptations preserve live/export behavior and binding boundaries."""
import subprocess
import sys

import modelx as mx

from lifelib.generator_models import apply_generators, apply_streams, _rewrite_streams


def test_boolean_overlay_preserves_results_and_shadowed_bindings(tmp_path):
    model = mx.new_model('GeneratorOverlay')
    try:
        s = model.new_space('Projection')
        s.new_cells('every', 'lambda n: all(i < 3 for i in range(n))')
        s.new_cells('some', 'lambda n: any(i == 2 for i in range(n))')
        s.new_cells('local', '''def local(n):
    all = lambda values: 17
    return all(i for i in range(n))
''')
        shadowed = model.new_space('Shadowed', refs={'all': sum})
        shadowed.new_cells('total', 'lambda n: all(i for i in range(n))')
        assert s.every(0) is True and s.every(4) is False
        assert s.some(0) is False and s.some(4) is True
        original = s.local.formula.source
        baseline = tmp_path / 'baseline_model'
        mx.write_model(model, baseline, backup=False)
        receipt = apply_generators(model)
        assert {r['cell'] for r in receipt} == {'GeneratorOverlay.Projection.every',
                                               'GeneratorOverlay.Projection.some'}
        assert s.local.formula.source == original
        assert s.local(8) == 17 and shadowed.total(4) == 6
        assert s.every(0) is True and s.every(5) is False
        assert s.some(0) is False and s.some(5) is True
        assert not apply_generators(model)
        saved = tmp_path / 'saved_model'
        mx.write_model(model, saved, backup=False)
        assert {p.relative_to(saved) for p in saved.rglob('*') if p.is_file()} == {
            p.relative_to(baseline) for p in baseline.rglob('*') if p.is_file()}
        reread = mx.read_model(saved, name='RereadOverlay')
        try:
            assert reread.Projection.every(7) is False
            assert reread.Projection.some(7) is True
        finally:
            reread.close()
        model.export(tmp_path / 'exported')
    finally:
        model.close()
    subprocess.run([sys.executable, '-c', '''from exported import mx_model
p = mx_model.Projection
assert p.every(0) is True and p.every(7) is False
assert p.some(0) is False and p.some(7) is True
assert p.local(7) == 17 and mx_model.Shadowed.total(4) == 6
'''], cwd=tmp_path, check=True)


def test_namespace_preserves_formulas_only_serialization(tmp_path):
    model = mx.new_model('FormulaOnly')
    try:
        s = model.new_space('Projection')
        s.new_cells('check', 'lambda n: all(i < 2 for i in range(n))')
        assert len(apply_generators(model)) == 1
        saved = tmp_path / 'model'
        mx.write_model(model, saved, backup=False)
        assert not (saved / '_data').exists()
        assert not list(saved.rglob('*.pickle'))
        reread = mx.read_model(saved, name='RereadFormulaOnly')
        try:
            assert reread.Projection.check(0) is True
            assert reread.Projection.check(3) is False
        finally:
            reread.close()
    finally:
        model.close()


def test_explicit_stream_overlay_preserves_consumers_and_saved_models(tmp_path):
    model = mx.new_model('ExplicitOverlay')
    try:
        s = model.new_space('Projection')
        s.new_cells('total', 'lambda n: sum(float(i) for i in range(n) if i % 2 == 0)')
        s.new_cells('every', 'lambda n: all(i < 3 for i in range(n))')
        s.new_cells('nested', 'lambda n: sum(float(g+z) for g in range(n) for z in range(g))')
        s.new_cells('pairs', 'lambda: tuple(a*b for a,b in [(1,2),(3,4)])')
        expected = {n: (s.total(n), s.every(n), s.nested(n)) for n in [0, 1, 3, 5]}
        receipt = apply_streams(model)
        assert len(receipt) == 4
        assert 'sum(over(' in s.total.formula.source
        assert 'flatten(over(' in s.nested.formula.source
        assert 'unpack' in s.pairs.formula.source
        assert all('sum_float' not in item['after'] for item in receipt)
        for n, values in expected.items():
            assert (s.total(n), s.every(n), s.nested(n)) == values
        assert type(s.total(0)) is int
        assert s.pairs() == (2, 12)
        assert apply_streams(model) == []
        saved = tmp_path / 'source'
        mx.write_model(model, saved, backup=False)
        restored = mx.read_model(saved, name='RestoredExplicit')
        try:
            assert restored.Projection.nested(5) == expected[5][2]
        finally:
            restored.close()
        model.export(tmp_path / 'exported')
    finally:
        model.close()
    subprocess.run([sys.executable, '-c', '''import pickle
from exported import mx_model
p=mx_model.Projection
assert p.total(0)==0 and type(p.total(0)) is int
assert p.total(5)==6.0 and p.pairs()==(2,12)
restored=pickle.loads(pickle.dumps(mx_model))
assert restored.Projection.nested(5)==p.nested(5)
'''], cwd=tmp_path, check=True)


def test_source_proposal_does_not_parse_an_ast_or_change_unsupported_captures(monkeypatch):
    import ast
    source = 'lambda n: sum(x for x in range(n))'
    unsafe = 'lambda n: (lambda: (z for z in range(x)) for x in range(n))'
    def forbidden(*args, **kwargs): raise AssertionError('AST source recognition')
    with monkeypatch.context() as patch:
        patch.setattr(ast, 'parse', forbidden)
        changed, used = _rewrite_streams(source)
        untouched, unused = _rewrite_streams(unsafe)
    assert 'over(range(n), lambda x: x)' in changed and used == ('over',)
    assert untouched == unsafe and unused == ()
