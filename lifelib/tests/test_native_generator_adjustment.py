"""Qualified generator source forms preserve order, laziness and public protocol."""
import pytest
from lifelib import expressions
from lifelib.generator_models import rewrite_native_generators


def compile_pair(source,globals):
    adjusted,operations=rewrite_native_generators(source)
    left=dict(globals);right=dict(globals,expressions=expressions)
    exec(source,left);exec(adjusted,right)
    assert operations
    return left['formula'],right['formula']


def test_filter_truth_is_evaluated_once_per_original_clause():
    source='def formula(n):\n    return tuple(x for x in range(n) if first(x) if second(x))\n'
    events=[]
    class Truth:
        def __init__(self,name,value):self.name,self.value=name,value
        def __bool__(self):events.append(self.name);return self.value
    def first(x):return Truth(('first',x),x>0)
    def second(x):return Truth(('second',x),x==2)
    left,right=compile_pair(source,{'first':first,'second':second})
    assert left(4)==(2,);expected=events.copy();events.clear()
    assert right(4)==(2,) and events==expected


def test_nested_bounds_are_lazy_and_flat_order_is_preserved():
    source='def formula(n):\n    return ((x,y) for x in range(n) for y in inner(x))\n'
    events=[]
    def inner(x):events.append(x);return range(x)
    left,right=compile_pair(source,{'inner':inner})
    for formula in [left,right]:
        events.clear();stream=formula(4)
        assert events==[] and next(stream)==(1,0) and events==[0,1]
        assert list(stream)==[(2,0),(2,1),(3,0),(3,1),(3,2)]


def test_mutable_consumer_keeps_send_throw_and_exception_identity():
    source='def formula(n):\n    return consume(x for x in range(n))\n'
    failure=LookupError('injected')
    def consume(stream):
        assert stream.send(None)==0
        assert stream.send('ignored')==1
        with pytest.raises(LookupError) as error:stream.throw(failure)
        assert error.value is failure
        assert list(stream)==[]
        return 17
    left,right=compile_pair(source,{'consume':consume})
    assert left(4)==right(4)==17


@pytest.mark.parametrize('source',[
 'def formula(n):\n    return (lambda: x for x in range(n))\n',
 'def formula(n):\n    return ((last := x) for x in range(n))\n',
 'def formula(n):\n    return (x+y for x in range(n) for y in range(y))\n',
 'def formula(n):\n    return (x for x,x in ((1,2),))\n',
 'def formula(n):\n    return ((x+y for y in range(2)) for x in range(n))\n',
 'def formula(expressions,n):\n    return (x for x in range(n))\n',
 'def formula(n):\n    return [x for x in range(n)]\n',
])
def test_unsupported_scope_forms_and_eager_comprehensions_stay_authored(source):
    assert rewrite_native_generators(source)==(source,[])
