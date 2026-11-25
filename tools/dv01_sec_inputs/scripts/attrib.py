"""Attribution experiments at 1 worker, book as pool_run (closes -1, 11, 23, all keys).
python attrib.py BUILD BOOK MODE OUT.json ; MODE = full | nocf | churn | churn_touch
full: pool_run's per-policy body; nocf: without the per-offset Python cashflow reads (values already cached);
churn: create and release every Valuation item, nothing computed; churn_touch: churn + one cheap Cell."""
import json, os, resource, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pool_run import setup

def main(build, book, mode, out):
    sys.setrecursionlimit(20000)
    sys.path.insert(0, str(Path(build).resolve()))
    from model_cy import mx_model as model
    cuts = setup(model, book, 2)
    V, A = model.Valuation, model.Actual
    ids = list(V.point_indices()); keys = range(len(model.Data.shock_key_months()))
    def policy(i):
        s = 1
        for m in cuts:
            for key in (-1, *keys):
                v = V[m, i, s, key]
                if mode in ('full', 'nocf'):
                    v.liability_pv()
                    if mode == 'full' and key == -1:
                        [v.cashflow_at_offset(k) for k in V.projection_months(m)]
                elif mode == 'churn_touch':
                    v.remaining_months()
                del v, V[m, i, s, key]
        if mode in ("full", "nocf"):
            del A[i, s, -1]
    r0, w0 = resource.getrusage(resource.RUSAGE_SELF), time.perf_counter()
    for i in ids:
        policy(i)
    w1, r1 = time.perf_counter(), resource.getrusage(resource.RUSAGE_SELF)
    res = {'mode': mode, 'wall': w1 - w0, 'user': r1.ru_utime - r0.ru_utime, 'system': r1.ru_stime - r0.ru_stime,
           'minflt': r1.ru_minflt - r0.ru_minflt, 'peak_rss_mib': r1.ru_maxrss / 1024}
    Path(out).write_text(json.dumps(res) + '\n'); print(json.dumps(res), flush=True)

if __name__ == '__main__':
    main(*sys.argv[1:5])
