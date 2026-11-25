"""Report-minus-setup Ir and LL misses by category: python cgcat.py MODEL_CY_DIR REP SETUP [POLICIES]"""
import re, sys, collections, json
sys.path.insert(0, '/home/user/c5/tools')
from cgx import diff
src = open(sys.argv[1] + '/_mx_classes.py').read()
owner = {}
for m in re.finditer(r'^def (\w+)\(self: (?:_mx_private_receiver\[)?(_c_\w+?)\]?[,)]', src, re.M):
    owner[m.group(1)] = m.group(2)
for m in re.finditer(r'^def (\w+)\(root: (_c_\w+)\)', src, re.M):
    owner[m.group(1)] = m.group(2)
ALLOC = re.compile(r'^(_?mi_|mi_|_PyObject_GC|PyObject_GC|PyType_GenericAlloc|gc_alloc|_PyObject_Malloc|_PyMem|PyMem|.*dealloc|subtype_dealloc|_PyObject_Free|free_|tupledealloc|_Py_Dealloc|.*_mx_values_alloc|__pyx_tp_dealloc|__pyx_tp_new|clear_slots|_PyObject_MallocWithType|_mi)')
REF = re.compile(r'^(_Py_MergeZeroLocalRefcount|_Py_DecRefShared|Py_DECREF|Py_INCREF|_Py_brc|_Py_ExplicitMergeRefcount|_Py_IncRefShared|_Py_DecRefSharedDebug|Py_XDECREF)')
def cat(ob, fn):
    fn = re.sub(r"'\d+$", '', fn or '?')
    if 'memset' in fn: return 'zeroing (memset)'
    if REF.match(fn): return 'reference counting'
    if ALLOC.match(fn) or 'dealloc' in fn: return 'allocation and release'
    if 'checked_cell_call' in fn or 'getattro' in fn or 'checked_cell_callable' in fn or 'exact_int64' in fn: return 'Python-level Cell calls (gate, getattr)'
    if ob.startswith(('libm', '_multiarray', 'libscipy', '_generator', 'libopenblas')): return 'math libraries'
    if ob.startswith('_mx_classes') or ob.startswith('_mx_helper') or ob.startswith('_mx_sys') or ob.startswith('_mx_collect'):
        m = re.search(r'_mx_classes_\d*(\w+?)$', fn)
        name = fn.split('_mx_classes_', 1)[-1] if '_mx_classes_' in fn else fn
        name = re.sub(r'^\d+', '', name).split('.')[0]
        cls = owner.get(name)
        if cls is None:
            mm = re.search(r'_c_(Valuation|Actual|Market|ESG|Outer|Data)', fn)
            cls = '_c_' + mm.group(1) if mm else None
        if 'collect' in fn.lower(): return 'collect machinery'
        return 'model code: ' + (cls or 'runtime/other')[3:] if cls else 'model code: runtime/other'
    if ob.startswith('python3'): return 'interpreter (driver, item construction)'
    return 'other: ' + ob[:12]
ev, d = diff(sys.argv[2], sys.argv[3])
n = float(sys.argv[4]) if len(sys.argv) > 4 else 1
I, M = ev.index('Ir'), [ev.index('DLmr'), ev.index('DLmw')]
D1 = [ev.index('D1mr'), ev.index('D1mw')]
o = collections.defaultdict(lambda: [0, 0, 0])
for (ob, fn), v in d.items():
    c = o[cat(ob, fn)]; c[0] += v[I]; c[1] += sum(v[i] for i in M); c[2] += sum(v[i] for i in D1)
tot = [sum(x[i] for x in o.values()) for i in range(3)]
res = {k: {'Ir_M_per_policy': round(v[0] / n / 1e6, 2), 'LL_misses_K_per_policy': round(v[1] / n / 1e3, 2), 'D1_misses_K_per_policy': round(v[2]/n/1e3, 1)} for k, v in sorted(o.items(), key=lambda kv: -kv[1][0])}
res['total'] = {'Ir_M_per_policy': round(tot[0] / n / 1e6, 2), 'LL_misses_K_per_policy': round(tot[1] / n / 1e3, 2), 'D1_misses_K_per_policy': round(tot[2]/n/1e3,1)}
print(json.dumps(res, indent=0))
