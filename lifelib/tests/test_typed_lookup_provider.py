"""Plain Cython cimports: no modelx/formula matcher is used for helper calls."""
import importlib
from pathlib import Path
import pickle
import subprocess
import sys
import pytest
import lifelib
from lifelib import typed_inputs as h
from lifelib.immutable_inputs import Table,Record,freeze

@pytest.fixture(scope='module')
def native(tmp_path_factory):
    root=tmp_path_factory.mktemp('explicit');provider=Path(lifelib.__file__).parent
    for ext in ['pyx','pxd']:(root/('native.'+ext)).write_bytes((provider/('_native_inputs.'+ext)).read_bytes())
    (root/'probe.pyx').write_text('''cimport native

def integer(function,source,key,*args):
    cdef long long value
    if not args:value=native.lookup_int(function,source,key)
    elif len(args)==1:value=native.lookup_int(function,source,key,args[0])
    else:value=native.lookup_int(function,source,key,args[0],args[1])
    return value

def floating(function,source,key,*args):
    cdef double value
    if not args:value=native.lookup_float(function,source,key)
    elif len(args)==1:value=native.lookup_float(function,source,key,args[0])
    else:value=native.lookup_float(function,source,key,args[0],args[1])
    return value

def boolean(function,source,key,*args):
    cdef bint value
    if not args:value=native.lookup_bool(function,source,key)
    elif len(args)==1:value=native.lookup_bool(function,source,key,args[0])
    else:value=native.lookup_bool(function,source,key,args[0],args[1])
    return value

def text(function,source,key,*args):
    cdef str value
    if not args:value=native.lookup_str(function,source,key)
    elif len(args)==1:value=native.lookup_str(function,source,key,args[0])
    else:value=native.lookup_str(function,source,key,args[0],args[1])
    return value

def raw(function,source,key,*args):
    if not args:return native.lookup_object(function,source,key)
    elif len(args)==1:return native.lookup_object(function,source,key,args[0])
    return native.lookup_object(function,source,key,args[0],args[1])
''')
    (root/'setup.py').write_text("from setuptools import setup\nfrom Cython.Build import cythonize\nsetup(ext_modules=cythonize(['native.pyx','probe.pyx'],compiler_directives={'language_level':3}))\n")
    r=subprocess.run([sys.executable,'setup.py','build_ext','--inplace'],cwd=root,capture_output=True,text=True)
    (root/'build.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
    sys.path.insert(0,str(root))
    try:yield importlib.import_module('probe')
    finally:sys.path.remove(str(root));sys.modules.pop('probe',None);sys.modules.pop('native',None)

@pytest.mark.parametrize('suffix,entry', [('int','integer'),('float','floating'),('bool','boolean'),('str','text')])
@pytest.mark.parametrize('value',[True,0,2**53+1,2.5,'2.5','bad',None,float('nan'),2**100])
def test_python_and_direct_native_contract(native,suffix,entry,value):
    function=getattr(h,'lookup_'+suffix);call=getattr(native,entry)
    for source,key,args in [(Record({'rate':value}),'rate',()),(Table((('M',42),),((value,),),('rate',)),('M',42),('rate',))]:
        try:expected=function(source,key,*args)
        except Exception as error:
            with pytest.raises(type(error)) as actual:call(function,source,key,*args)
            assert actual.value.args==error.args
        else:
            actual=call(function,source,key,*args)
            assert type(actual)is type(expected)
            assert actual==expected or isinstance(actual,float) and actual!=actual and expected!=expected


def test_direct_calls_use_no_python_table_or_helper_functions(native):
    source=Table((('M',42),),((1.5,3,'Y',True),),('rate','age','label','flag'))
    record=Record({'age':3,'rate':1.5,'flag':True,'label':'Y'})
    codes={getattr(h,'lookup_'+s).__code__ for s in ['int','float','bool','str']}
    codes.update([h.lookup.__code__,h._typed_value.__code__,Table.__getitem__.__code__,Table.__init__.__code__,Record.__getitem__.__code__,freeze.__code__])
    calls=[]
    def profile(frame,event,arg):
        if event=='call' and frame.f_code in codes:calls.append(frame.f_code.co_name)
    sys.setprofile(profile)
    try:
        assert native.floating(h.lookup_float,source,('M',42),'rate')==1.5
        assert native.integer(h.lookup_int,source,('M',42),'age')==3
        assert native.text(h.lookup_str,source,('M',42),'label')=='Y'
        assert native.boolean(h.lookup_bool,source,('M',42),'flag') is True
        assert native.integer(h.lookup_int,record,'age')==3
        assert native.floating(h.lookup_float,record,'rate')==1.5
        assert native.boolean(h.lookup_bool,record,'flag') is True
        assert native.text(h.lookup_str,record,'label')=='Y'
    finally:sys.setprofile(None)
    assert calls==[]


def test_defaults_replacement_pickle_and_at_error(native):
    import pandas as pd
    from lifelib.pandas_inputs import table
    record=Record({'age':3})
    assert native.integer(h.lookup_int,record,'absent',7)==7
    source=Table((),(),('rate',))
    assert native.floating(h.lookup_float,source,0,'rate','2.5')==2.5
    seen=[]
    def replacement(*args):seen.append(args);return 3.5
    assert native.floating(replacement,source,0,'rate')==3.5
    assert seen==[(source,0,'rate')]
    frame=pd.DataFrame({'rate':[1.5,2.5]},index=pd.MultiIndex.from_tuples([('M',42),('F',43)]))
    owned=table(frame,indexing='at')
    assert native.floating(h.lookup_float,pickle.loads(pickle.dumps(owned)),('M',42),'rate')==1.5
    with pytest.raises(KeyError) as error:native.floating(h.lookup_float,owned,('M',43),'rate')
    assert error.value.args==(15,)


@pytest.mark.parametrize('keys,query',[
    ((1,2),1.0), ((1.0,2.0),1), ((True,False),1.0),
    ((-0.0,1.0),0), ((0,1),-0.0),
    ((1.5,2.5),1.5), ((1.5,2.5),1),
    ((2**53,2**53+1),float(2**53+1)),
    ((float(2**53),float(2**53+2)),2**53+1),
    ((float(2**63),-1.5),2**63-1),
    ((("M",42.5),("F",43.5)),("M",42.5)),
])
def test_float_keys_preserve_exact_numeric_equality(native,keys,query):
    table=Table(keys,[(float(i+1),) for i in range(len(keys))],('rate',))
    try:expected=h.lookup_float(table,query,'rate')
    except Exception as error:
        with pytest.raises(type(error)) as actual:native.floating(h.lookup_float,table,query,'rate')
        assert actual.value.args==error.args
    else:assert native.floating(h.lookup_float,table,query,'rate')==expected


def test_float_keys_are_native_not_a_python_helper_fallback(native):
    table=Table((35.5,40.5),((1.5,),(2.5,)),('rate',));calls=[]
    def profile(frame,event,arg):
        if event=='call' and frame.f_code in {h.lookup_float.__code__,h.lookup.__code__,Table.lookup.__code__}:
            calls.append(frame.f_code.co_name)
    sys.setprofile(profile)
    try:assert native.floating(h.lookup_float,table,35.5,'rate')==1.5
    finally:sys.setprofile(None)
    assert not calls


def test_object_lookup_keeps_missing_identity(native):
    import pandas as pd
    for value in [pd.NA,pd.NaT,None]:
        record=Record({'value':value})
        assert native.raw(h.lookup_object,record,'value') is value
        assert h.lookup_object(record,'value') is value
    assert native.raw(h.lookup_object,Record({}),'absent',None) is None
