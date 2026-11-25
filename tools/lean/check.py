"""Check a lean model against the upstream model, live, on the shipped book.

    python tools/lean/check.py --upstream <pristine upstream checkout> --out <lean tree> MODEL ...

Both models are read with modelx in one process.  For every model point of the shipped
``model_point_table`` and every public cell of ``Projection`` (and of ``Data``) that takes
no argument, the lean value must equal the upstream value exactly: frames and series by
``pandas.testing.assert_*_equal(check_exact=True)`` (index, columns and dtypes included),
floats bit for bit (NaN equal to NaN), and a member equal to the upstream label it stands
for (``Sex.F``, whose value is ``"F"``).  A cell that raises must raise the same exception type with
the same message in both.  Prints one JSON line per model: values compared, cells, points,
mismatches.
"""

import argparse
import enum
import os
import json
import math
import pathlib
import sys
import traceback

import modelx as mx
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from catalog import discover, model_dir  # noqa: E402


def norm(v):
    if isinstance(v, enum.Enum):
        return v.value          # a StrEnum member: upstream's label text
    return v


def same(a, b, loose=False):
    """(equal, number of values compared); ``loose``: a tuple may stand for a list"""
    if isinstance(a, pd.DataFrame) or isinstance(b, pd.DataFrame):
        a2 = a.map(norm) if isinstance(b, pd.DataFrame) else a
        try:
            pd.testing.assert_frame_equal(a2, b.map(norm) if isinstance(b, pd.DataFrame) else b,
                                          check_exact=True)
        except AssertionError:
            return False, getattr(a, "size", 1)
        return True, a.size
    if isinstance(a, pd.Series) or isinstance(b, pd.Series):
        try:
            pd.testing.assert_series_equal(a.map(norm), b.map(norm), check_exact=True)
        except (AssertionError, AttributeError):
            return False, getattr(a, "size", 1)
        return True, a.size
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if (type(a) is not type(b) and not loose) or len(a) != len(b):  # a tuple stays a tuple
            return False, len(a)
        n, ok = 0, True
        for x, y in zip(a, b):
            e, k = same(x, y, loose)
            ok &= e
            n += k
        return ok, n
    if isinstance(a, dict) and isinstance(b, dict):
        if list(map(norm, a)) != list(map(norm, b)):
            return False, len(a)
        n, ok = 0, True
        for x, y in zip(a.values(), b.values()):
            e, k = same(x, y)
            ok &= e
            n += k
        return ok, n
    a, b = norm(a), norm(b)
    if isinstance(a, pathlib.PurePath) and isinstance(b, pathlib.PurePath):
        return a.name == b.name, 1        # the two trees differ; the folder must not
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True, 1
        return (a == b and math.copysign(1, a) == math.copysign(1, b)), 1
    if type(a) is not type(b) and not (isinstance(a, bool) and isinstance(b, bool)):
        # int vs numpy int etc. must still be the same type to be "exact"
        return False, 1
    try:
        return bool(a == b), 1
    except Exception:
        return repr(a) == repr(b), 1


def value(f):
    try:
        return ("ok", f())
    except Exception as e:              # noqa: BLE001
        cause = e
        while getattr(cause, "__cause__", None) is not None:
            cause = cause.__cause__
        return ("err", type(e).__name__, type(cause).__name__, str(cause).split("\n")[0][:200])


def zero_arg_cells(space):
    out = []
    for name, cells in space.cells.items():
        if name.startswith("_"):
            continue
        if not cells.parameters:
            out.append(name)
    return sorted(out)


def tuple_cells(name):
    """The cells the lean text returns as a tuple where upstream returns a list."""
    import tomllib
    path = HERE / "overrides" / (name + ".toml")
    if not path.exists():
        return set()
    with path.open("rb") as f:
        return set(tomllib.load(f).get("tuple_cells", {}).get("Projection", []))


def compare(up_dir, lean_dir, name):
    up = mx.read_model(up_dir, name=name + "_up")
    lean = mx.read_model(lean_dir, name=name + "_lean")
    try:
        total, cells_n, bad = 0, 0, []
        for sname in ("Data",):
            if sname in up.spaces:
                for c in zero_arg_cells(up.spaces[sname]):
                    a, b = value(lean.spaces[sname].cells[c]), value(up.spaces[sname].cells[c])
                    cells_n += 1
                    if a[0] != b[0] or (a[0] == "err" and a[2:] != b[2:]):
                        bad.append((sname, c, None, str(a)[:120], str(b)[:120]))
                        continue
                    if a[0] == "err":
                        total += 1
                        continue
                    ok, n = same(a[1], b[1])
                    total += n
                    if not ok:
                        bad.append((sname, c, None, "differs", ""))
        keys = list(up.Data.model_point_table().index)
        names = zero_arg_cells(up.Projection)
        loose = tuple_cells(name)
        for key in keys:
            pu, pl = up.Projection[key], lean.Projection[key]
            for c in names:
                a, b = value(getattr(pl, c)), value(getattr(pu, c))
                cells_n += 1
                if a[0] != b[0] or (a[0] == "err" and a[2:] != b[2:]):
                    bad.append(("Projection", c, str(key), str(a)[:160], str(b)[:160]))
                    continue
                if a[0] == "err":
                    total += 1
                    continue
                ok, n = same(a[1], b[1], c in loose)
                if ok and c in loose and not isinstance(a[1], tuple):
                    ok = False                  # a tuple_cells cell must return a tuple
                total += n
                if not ok:
                    bad.append(("Projection", c, str(key), "differs", ""))
        return {"model": name, "points": len(keys), "cells": len(names), "evaluations": cells_n,
                "values": total, "mismatches": len(bad), "first": bad[:int(os.environ.get("CHECK_SHOW", "5"))]}
    finally:
        up.close()
        lean.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("models", nargs="+")
    args = ap.parse_args()
    found = {m: (lib, p) for lib, p, m in discover(args.upstream)}
    for m in args.models:
        lib, p = found[m]
        try:
            r = compare(model_dir(args.upstream, lib, p, m), model_dir(args.out, lib, p, m), m)
        except Exception:               # noqa: BLE001
            r = {"model": m, "error": traceback.format_exc()[-800:]}
        print(json.dumps(r), flush=True)


if __name__ == "__main__":
    main()
