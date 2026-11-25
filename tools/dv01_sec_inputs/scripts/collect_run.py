"""Collect route, one fresh process: Outer.annual_risk_report(PATHS, STEPS) with model.collect_workers = WORKERS
(after A2's scale_probe.py). Same output fields as pool_run.py.
    python collect_run.py BUILD BOOK WORKERS OUT.json [--steps 2] [--paths 1] [--frames DIR] [--setup-only]"""
import json, resource, sys, time
from pathlib import Path


def main():
    a = sys.argv[1:]
    build, book, workers, out = a[0], a[1], int(a[2]), Path(a[3])
    steps = int(a[a.index('--steps') + 1]) if '--steps' in a else 2
    paths = int(a[a.index('--paths') + 1]) if '--paths' in a else 1
    frames = Path(a[a.index('--frames') + 1]) if '--frames' in a else None
    sys.setrecursionlimit(20000)
    sys.path.insert(0, str(Path(build).resolve()))
    from model_cy import mx_model as model
    cuts = tuple(12 * y - 1 for y in range(steps + 1))
    model.Actual.snapshot_months = tuple(m for m in cuts if m >= 0)
    model.Actual.projection_months = tuple(range(12 * steps))
    model.Actual.last_snapshot_month = model.Valuation.last_snapshot_month = cuts[-1]
    if hasattr(model.Valuation, 'snapshot_months'):
        model.Valuation.snapshot_months = model.Actual.snapshot_months
    model.collect_workers = workers
    model.path = Path(book).resolve() / 'model'
    for name in ('model_point_table', 'mort_table', 'surr_charge_table', 'surr_charge_age_cap_table',
                 'withdrawal_table', 'mva_factor_table', 'shock_key_months'):
        getattr(model.Data, name)()
    model.ESG.param_table()
    model.ESG.curve_knots()
    if '--setup-only' in a:
        print('setup only', flush=True)
        return
    r0, c0, w0 = resource.getrusage(resource.RUSAGE_SELF), time.process_time(), time.perf_counter()
    dv, cs = model.Outer.annual_risk_report(paths, steps)
    w1, c1, r1 = time.perf_counter(), time.process_time(), resource.getrusage(resource.RUSAGE_SELF)
    res = {'build': build, 'workers': workers, 'route': 'collect', 'wall': w1 - w0, 'cpu': c1 - c0,
           'user': r1.ru_utime - r0.ru_utime, 'system': r1.ru_stime - r0.ru_stime,
           'peak_rss_mib': r1.ru_maxrss / 1024, 'minflt': r1.ru_minflt - r0.ru_minflt, 'majflt': r1.ru_majflt - r0.ru_majflt, 'vol_cs': r1.ru_nvcsw - r0.ru_nvcsw, 'invol_cs': r1.ru_nivcsw - r0.ru_nivcsw, 'rss_before_mib': r0.ru_maxrss / 1024,
           'policies': len(model.Valuation.point_indices()), 'steps': steps, 'paths': paths,
           'gil': sys._is_gil_enabled(), 'dv01_total': float(dv.to_numpy().sum()),
           'cs01_total': float(cs.to_numpy().sum())}
    if frames:
        frames.mkdir(parents=True, exist_ok=True)
        dv.to_csv(frames / f'DV01-{out.stem}.csv')
        cs.to_csv(frames / f'CS01-{out.stem}.csv')
    out.write_text(json.dumps(res) + '\n')
    print(json.dumps(res), flush=True)


if __name__ == '__main__':
    main()
