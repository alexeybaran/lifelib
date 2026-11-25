"""4 threads create and release Valuation items only: python churn4.py BUILD BOOK WORKERS [sleep]"""
import json, resource, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pool_run import setup
build, book, w = sys.argv[1], sys.argv[2], int(sys.argv[3]); slp = len(sys.argv) > 4
sys.path.insert(0, str(Path(build).resolve()))
from model_cy import mx_model as model
cuts = setup(model, book, 2)
V = model.Valuation; ids = list(V.point_indices())
def pol(i):
    for m in cuts:
        for key in range(-1, 13):
            v = V[m, i, 1, key]; v.remaining_months(); del v, V[m, i, 1, key]
            if slp: time.sleep(0)
r0, w0 = resource.getrusage(resource.RUSAGE_SELF), time.perf_counter()
with ThreadPoolExecutor(w) as p: list(p.map(pol, ids))
r1 = resource.getrusage(resource.RUSAGE_SELF)
print(json.dumps({'w': w, 'sleep': slp, 'wall': round(time.perf_counter() - w0, 3), 'sys': round(r1.ru_stime - r0.ru_stime, 2), 'minflt': r1.ru_minflt - r0.ru_minflt, 'rss': r1.ru_maxrss // 1024}))
