"""Self cost per (object, function) with all events from a callgrind file; report-minus-setup diffs.
  python cgx.py top REPORT.out SETUP.out [N] [EVENT]
"""
import collections, re, sys

def parse(path):
    names = {'ob': {}, 'fn': {}, 'fl': {}}
    ob = fn = None; events = None; after_calls = False
    cost = collections.defaultdict(lambda: None)
    tot = None
    for line in open(path, errors='replace'):
        line = line.rstrip('\n')
        if line.startswith('events:'):
            events = line.split()[1:]; tot = [0] * len(events); continue
        m = re.match(r'^(c?)(ob|fn|fl|fi|fe)=(?:\((\d+)\))?\s*(.*)$', line)
        if m:
            callee, kind, ident, name = m.groups()
            table = names['fl' if kind in ('fi', 'fe') else kind]
            if ident is not None:
                if name: table[ident] = name
                name = table.get(ident, name)
            if not callee:
                if kind == 'ob': ob = name
                elif kind == 'fn': fn = name
            continue
        if line.startswith('calls='):
            after_calls = True; continue
        if line and (line[0].isdigit() or line[0] in '+-*'):
            parts = line.split()
            if after_calls:
                after_calls = False; continue
            vals = [int(x) for x in parts[1:]]
            key = ((ob or '?').split('/')[-1], fn)
            c = cost[key]
            if c is None: c = cost[key] = [0] * len(events)
            for i, v in enumerate(vals): c[i] += v; tot[i] += v
    return events, dict(cost), tot

def diff(rep, setup):
    ev, r, _ = parse(rep); _, s, _ = parse(setup)
    out = {}
    for k in set(r) | set(s):
        a = r.get(k) or [0] * len(ev); b = s.get(k) or [0] * len(ev)
        out[k] = [x - y for x, y in zip(a, b)]
    return ev, out

if __name__ == '__main__':
    ev, d = diff(sys.argv[2], sys.argv[3])
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 40
    e = ev.index(sys.argv[5]) if len(sys.argv) > 5 else 0
    tot = [sum(v[i] for v in d.values()) for i in range(len(ev))]
    print('total', dict(zip(ev, tot)))
    for k, v in sorted(d.items(), key=lambda kv: -kv[1][e])[:n]:
        print(f'{v[e]:>14,} {v[ev.index("D1mr")]:>10,} {v[ev.index("DLmr")]+v[ev.index("DLmw")]:>9,}  {k[0][:22]:22} {(k[1] or "")[:110]}')
