"""Compare report-minus-setup self costs of two builds by normalized function name.
python cgcmp.py A_rep A_setup B_rep B_setup [N]"""
import re, sys, collections
sys.path.insert(0, '/home/user/c5/tools')
from cgx import diff
def norm(k):
    ob, fn = k; fn = fn or '?'
    fn = re.sub(r"'\d+$", '', fn)
    return (ob.split('.')[0][:14], fn)
def agg(r, s):
    ev, d = diff(r, s); o = collections.defaultdict(lambda: [0]*len(ev))
    for k, v in d.items():
        t = o[norm(k)]
        for i, x in enumerate(v): t[i] += x
    return ev, o
ev, a = agg(sys.argv[1], sys.argv[2]); _, b = agg(sys.argv[3], sys.argv[4])
n = int(sys.argv[5]) if len(sys.argv) > 5 else 50
I, M = ev.index('Ir'), [ev.index(x) for x in ('DLmr','DLmw')]
rows = []
for k in set(a) | set(b):
    va = a.get(k, [0]*len(ev)); vb = b.get(k, [0]*len(ev))
    rows.append((va[I]-vb[I], va[I], vb[I], sum(va[m] for m in M), sum(vb[m] for m in M), k))
rows.sort(key=lambda r: -abs(r[0]))
print('tot A', sum(v[I] for v in a.values()), 'tot B', sum(v[I] for v in b.values()))
for r in rows[:n]:
    print(f'{r[0]:>13,} {r[1]:>13,} {r[2]:>13,} LLm {r[3]:>8,} {r[4]:>8,}  {r[5][0]:14} {r[5][1][:90]}')
