"""Compare DV01/CS01 report frames: python compare_frames.py REF_DIR REF_MODE GOT_DIR GOT_MODE [rtol atol]"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def main(ref, ref_mode, got, got_mode, rtol=1e-10, atol=1e-7):
    out = {}
    for name in ('DV01', 'CS01'):
        a = pd.read_csv(Path(ref) / f'{name}-{ref_mode}.csv', index_col=[0, 1]).to_numpy()
        b = pd.read_csv(Path(got) / f'{name}-{got_mode}.csv', index_col=[0, 1]).to_numpy()
        d = np.abs(a - b)
        out[name] = {'values': int(a.size), 'max_abs': float(d.max()),
                     'max_rel': float((d / np.maximum(np.abs(a), 1e-300)).max()),
                     'within': bool((d <= np.maximum(atol, rtol * np.abs(a))).all()),
                     'total_ref': float(a.sum()), 'total_got': float(b.sum())}
    print(json.dumps(out))
    return out


if __name__ == '__main__':
    args = sys.argv[1:5]
    tol = [float(x) for x in sys.argv[5:7]]
    main(*args, *tol)
