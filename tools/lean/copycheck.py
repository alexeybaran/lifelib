"""Copy a library with lifelib's normal route and run a copied lean model without lifelib.

    python tools/lean/copycheck.py --upstream <pristine upstream> --out <lean tree> MODEL ...

``lifelib.create(<lib>, <dir>)`` (the lean tree's lifelib) copies the library; a child
process whose ``sys.path`` holds modelx and site-packages but no lifelib (``python -s``),
then asserts ``find_spec("lifelib") is None``, reads the copied model, checks that its
enum References are the classes of the module stored in the copy, and compares it with
the upstream model exactly (``check.compare``).
"""

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from catalog import discover  # noqa: E402

CHILD = r'''
import importlib.util, json, sys
assert importlib.util.find_spec("lifelib") is None, "lifelib is importable"
sys.path.insert(0, %(here)r)
import modelx as mx
from check import compare
copied = %(copied)r
m = mx.read_model(copied, name="copied_probe")
try:
    mod = getattr(m, "enums", None)
    classes = [n for n in m.Projection.refs if isinstance(m.Projection.refs[n], type)]
    stored = all(m.Projection.refs[n] is getattr(mod, n) for n in classes) if mod else not classes
    where = mod.__file__ if mod else None
finally:
    m.close()
r = compare(%(up)r, copied, %(name)r)
r["enum_refs_from_copy"] = stored
r["enums_file"] = where
print(json.dumps(r))
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--modelx", required=True, help="folder holding the modelx package")
    ap.add_argument("models", nargs="+")
    args = ap.parse_args()
    found = {m: (lib, p) for lib, p, m in discover(args.out)}
    sys.path.insert(0, str(pathlib.Path(args.out).resolve()))
    import lifelib
    assert pathlib.Path(lifelib.__file__).resolve().is_relative_to(pathlib.Path(args.out).resolve())
    with tempfile.TemporaryDirectory() as tmp:
        made = {}
        for m in args.models:
            lib, prod = found[m]
            if lib not in made:
                dst = pathlib.Path(tmp) / lib
                lifelib.create(lib, str(dst))
                made[lib] = dst
            copied = made[lib] / "products" / prod / m
            up = pathlib.Path(args.upstream) / "lifelib" / "libraries" / lib / "products" / prod / m
            code = CHILD % {"here": str(HERE), "copied": str(copied), "up": str(up), "name": m}
            env = {"PYTHONPATH": args.modelx, "PATH": "/usr/bin:/bin"}
            res = subprocess.run([sys.executable, "-s", "-c", code], capture_output=True, text=True,
                                 env=env, cwd=tmp)
            line = [x for x in res.stdout.splitlines() if x.startswith("{")]
            print(line[-1] if line else json.dumps({"model": m, "error": res.stderr[-1500:]}),
                  flush=True)


if __name__ == "__main__":
    main()
