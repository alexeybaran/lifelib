"""Direct route, one task per policy over a concurrent.futures.ThreadPoolExecutor (WORKERS threads).
Each task values its policy at every close and curve (Valuation items released after use, Actual item
released when the policy is done) and returns its liability PVs and base cash flows; the report is then
assembled in policy order exactly as Outer's direct cells sum it (dv01 = base - shocked; cs01 from the
summed base cash flows discounted on the shocked curve).
    python pool_run_c5.py BUILD BOOK WORKERS OUT.json [--steps 2] [--paths 1] [--frames DIR] [--outer] [--map]
--outer: one worker, no pool: the model's own Outer cells (A2's direct-release loop), for checking."""
import json, os, resource, sys, time
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path
import numpy as np
import pandas as pd


def setup(model, book, steps):
    cuts = tuple(12 * y - 1 for y in range(steps + 1))
    model.Actual.snapshot_months = tuple(m for m in cuts if m >= 0)
    model.Actual.projection_months = tuple(range(12 * steps))
    model.Actual.last_snapshot_month = model.Valuation.last_snapshot_month = cuts[-1]
    if hasattr(model.Valuation, 'snapshot_months'):
        model.Valuation.snapshot_months = model.Actual.snapshot_months
    model.path = Path(book).resolve() / 'model'
    for name in ('model_point_table', 'mort_table', 'surr_charge_table', 'surr_charge_age_cap_table',
                 'withdrawal_table', 'mva_factor_table', 'shock_key_months'):
        getattr(model.Data, name)()
    model.ESG.param_table()
    model.ESG.curve_knots()
    return cuts


def report_pool(model, cuts, paths, workers):
    V, A = model.Valuation, model.Actual
    ids = list(V.point_indices())
    keys = range(len(model.Data.shock_key_months()))
    scens = range(1, paths + 1)

    def policy(i):
        out = {}
        for s in scens:
            for m in cuts:
                v = V[m, i, s, -1]
                pv = v.liability_pv()
                cf = [v.cashflow_at_offset(k) for k in V.projection_months(m)]
                del v, V[m, i, s, -1]
                shocked = []
                for key in keys:
                    v = V[m, i, s, key]
                    shocked.append(v.liability_pv())
                    del v, V[m, i, s, key]
                out[s, m] = (pv, cf, shocked)
            del A[i, s, -1]
        return out

    if '--prewarm' in sys.argv:          # diagnostic: shared Market/ESG caches filled by one policy, untimed
        policy(ids[0])
        globals()['_w0'] = time.perf_counter()
    if workers == 1:
        results = [policy(i) for i in ids]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            if '--map' in sys.argv:      # D0's driver: the main thread waits on each future in turn
                results = list(pool.map(policy, ids))
            else:                        # C5: one wait for all futures (see C5-SHARED-ITEMS.md)
                futures = [pool.submit(policy, i) for i in ids]
                wait(futures)
                results = [f.result() for f in futures]
    dv_rows, cs_rows = [], []
    for s in scens:
        for m in cuts:
            base = 0.0
            for r in results:
                base += r[s, m][0]
            offsets = list(V.projection_months(m))
            cf = {k: 0.0 for k in offsets}
            for r in results:
                for k, x in zip(offsets, r[s, m][1]):
                    cf[k] += x
            dv, cs = [], []
            for key in keys:
                shocked = 0.0
                for r in results:
                    shocked += r[s, m][2][key]
                dv.append(base - shocked)
                market = model.Market(m + 1, s, key)
                discounts = [market.price(m + k + 2) for k in cf]
                cs.append(base - float(-np.dot(tuple(cf.values()), discounts)))
            dv_rows.append(dv)
            cs_rows.append(cs)
    index = pd.MultiIndex.from_product([scens, range(len(cuts))], names=['scenario', 'year'])
    cols = pd.Index(model.Data.shock_key_months(), name='tenor_months')
    return pd.DataFrame(dv_rows, index=index, columns=cols), pd.DataFrame(cs_rows, index=index, columns=cols)


def report_outer(model, cuts, paths):
    outer, V = model.Outer, model.Valuation
    ids = V.point_indices()
    keys = range(len(model.Data.shock_key_months()))
    for s in range(1, paths + 1):
        for m in cuts:
            outer.base_liability_pv(m, s)
            outer.base_cashflows(m, s)
            for p in ids:
                del V[m, p, s, -1]
            for key in keys:
                outer.dv01(m, s, key)
                outer.cs01(m, s, key)
                for p in ids:
                    del V[m, p, s, key]
    return outer.annual_risk_report(paths, len(cuts) - 1)


def main():
    a = sys.argv[1:]
    build, book, workers, out = a[0], a[1], int(a[2]), Path(a[3])
    steps = int(a[a.index('--steps') + 1]) if '--steps' in a else 2
    paths = int(a[a.index('--paths') + 1]) if '--paths' in a else 1
    frames = Path(a[a.index('--frames') + 1]) if '--frames' in a else None
    sys.setrecursionlimit(20000)
    if build == 'live':
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import importlib
        model = importlib.import_module(os.environ.get('DV01_PKG', 'dv01_sec_d')).build_model(
            route='direct', sec_model=Path(book) / 'MYGA_US_SEC')
    else:
        sys.path.insert(0, str(Path(build).resolve()))
        from model_cy import mx_model as model, _mx_classes
        assert Path(_mx_classes.__file__).suffix == '.so'
    cuts = setup(model, book, steps)
    if '--setup-only' in a:
        print('setup only', flush=True)
        return
    r0, c0, w0 = resource.getrusage(resource.RUSAGE_SELF), time.process_time(), time.perf_counter()
    if '--outer' in a:
        dv, cs = report_outer(model, cuts, paths)
    else:
        dv, cs = report_pool(model, cuts, paths, workers)
    w1, c1, r1 = time.perf_counter(), time.process_time(), resource.getrusage(resource.RUSAGE_SELF)
    if '_w0' in globals():
        w0 = globals()['_w0']
    res = {'build': build, 'workers': workers, 'outer': '--outer' in a, 'wall': w1 - w0, 'cpu': c1 - c0,
           'user': r1.ru_utime - r0.ru_utime, 'system': r1.ru_stime - r0.ru_stime,
           'peak_rss_mib': r1.ru_maxrss / 1024, 'minflt': r1.ru_minflt - r0.ru_minflt, 'majflt': r1.ru_majflt - r0.ru_majflt, 'vol_cs': r1.ru_nvcsw - r0.ru_nvcsw, 'invol_cs': r1.ru_nivcsw - r0.ru_nivcsw, 'rss_before_mib': r0.ru_maxrss / 1024,
           'policies': len(model.Valuation.point_indices()), 'steps': steps, 'paths': paths,
           'gil': sys._is_gil_enabled(), 'dv01_total': float(dv.to_numpy().sum()),
           'cs01_total': float(cs.to_numpy().sum())}
    if frames:
        frames.mkdir(parents=True, exist_ok=True)
        tag = out.stem
        dv.to_csv(frames / f'DV01-{tag}.csv')
        cs.to_csv(frames / f'CS01-{tag}.csv')
    out.write_text(json.dumps(res) + '\n')
    print(json.dumps(res), flush=True)


if __name__ == '__main__':
    main()
