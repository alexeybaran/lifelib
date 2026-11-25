"""Passes over every point: build Projection[idx], result_cf(), del. python ir_sec.py OUT NAME PASSES"""
import sys
from pathlib import Path
out, name, passes = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
sys.path.insert(0, str(out)); sys.setrecursionlimit(20000)
import importlib
model = importlib.import_module(f'{name}_nomx_cy').mx_model
P = model.Projection
n = len(model.Data.model_point_table())
for _ in range(passes):
    for i in range(n):
        P[i].result_cf()
        del P[i]
print('points', n)
