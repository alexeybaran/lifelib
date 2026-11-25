"""Compiled result_cf of every point against live modelx: python values_sec.py PRODUCT_DIR NAME OUT"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
product, name, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
sys.path.insert(0, str(out)); sys.setrecursionlimit(20000)
import importlib, modelx as mx
cy = importlib.import_module(f'{name}_nomx_cy').mx_model
live = mx.read_model(product / name)
table = live.Data.model_point_table()
keys = list(table.index) if tuple(live.Projection.parameters) != ('idx',) else list(range(len(table)))
worst, n = 0.0, 0
for i, k in enumerate(keys):
    a = live.Projection[k].result_cf(); b = cy.Projection[i].result_cf()
    a = np.asarray(pd.DataFrame(a).to_numpy(), float); b = np.asarray(pd.DataFrame(b).to_numpy(), float)
    assert a.shape == b.shape
    d = np.abs(a - b); ok = (d <= np.maximum(1e-7, 1e-10 * np.abs(a))).all()
    assert ok, (k, d.max()); worst = max(worst, float(d.max())); n += a.size
print(json.dumps({'model': name, 'points': len(keys), 'values': n, 'max_abs': worst, 'within': True}))
