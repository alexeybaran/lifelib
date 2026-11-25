"""Lines added/removed per model: lean vs upstream, and the full conversion vs v0.17.3.

    python tools/lean/diffsize.py --upstream <upstream checkout> --out <lean tree>
                                  [--ref <full conversion checkout> --base <v0.17.3 checkout>]
                                  [MODEL ...]

Counts ``difflib`` line changes for Projection, Data, the enums module (lean: in the model
folder; full: in the product folder) and the product's spec.py.  The model ``__init__.py``
(+4/5 lines for the ``enums`` Reference) and the binary ``_data`` files are not counted.
"""

import argparse
import difflib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from catalog import discover, model_dir, product_dir  # noqa: E402


def lines(path):
    p = pathlib.Path(path)
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


def count(a, b):
    add = rem = 0
    for op in difflib.ndiff(a, b) if False else difflib.unified_diff(a, b, n=0, lineterm=""):
        if op.startswith("+") and not op.startswith("+++"):
            add += 1
        elif op.startswith("-") and not op.startswith("---"):
            rem += 1
    return add, rem


def sizes(up_root, new_root, lib, prod, model, enums_in_model):
    out = {}
    for s in ("Projection", "Data"):
        out[s] = count(lines(model_dir(up_root, lib, prod, model) / s / "__init__.py"),
                       lines(model_dir(new_root, lib, prod, model) / s / "__init__.py"))
    enums = (model_dir(new_root, lib, prod, model) / "enums.py" if enums_in_model
             else product_dir(new_root, lib, prod) / "enums.py")
    out["enums"] = count([], lines(enums))
    out["spec"] = count(lines(product_dir(up_root, lib, prod) / "spec.py"),
                        lines(product_dir(new_root, lib, prod) / "spec.py"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref")
    ap.add_argument("--base")
    ap.add_argument("models", nargs="*")
    args = ap.parse_args()
    for lib, prod, model in discover(args.out):
        if args.models and model not in args.models:
            continue
        r = {"model": model, "lean": sizes(args.upstream, args.out, lib, prod, model, True)}
        if args.ref:
            r["full"] = sizes(args.base, args.ref, lib, prod, model, False)
        print(json.dumps(r))


if __name__ == "__main__":
    main()
