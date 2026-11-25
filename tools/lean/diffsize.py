"""Lines added/removed per model: lean vs upstream, and the full conversion vs v0.17.3.

    python tools/lean/diffsize.py --upstream <upstream checkout> --out <lean tree>
                                  [--ref <full conversion checkout> --base <v0.17.3 checkout>]
                                  [MODEL ...]

Counts ``difflib`` line changes for Projection, Data, the enums module (lean: in the model
folder; full: in the product folder) and the product's spec.py.  The model ``__init__.py``
(+4/5 lines for the ``enums`` Reference) and the binary ``_data`` files are not counted.

The lean Projection/Data lines are also classified (``kinds``): ``rename`` (a changed
line that is upstream's line once each ``Family.MEMBER`` is read as its label text),
``refs`` (the added ``Family = ("Pickle", n)`` References and their blank lines) and
``other`` (added lines of any other kind).
"""

import argparse
import ast
import difflib
import re
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


def members(enums_path):
    """{"Family.MEMBER": label} of a lean enums.py."""
    out = {}
    if not pathlib.Path(enums_path).exists():
        return out
    for node in ast.parse(pathlib.Path(enums_path).read_text(encoding="utf-8")).body:
        if isinstance(node, ast.ClassDef):
            for a in node.body:
                if isinstance(a, ast.Assign) and isinstance(a.value, ast.Constant):
                    out["%s.%s" % (node.name, a.targets[0].id)] = a.value.value
    return out


def classify(a, b, mem):
    """{kind: added lines} of the lean text ``b`` against upstream ``a``."""
    kinds = {"rename": 0, "refs": 0, "other": 0}
    pat = re.compile(r"\b(%s)\b" % "|".join(re.escape(k) for k in sorted(mem, key=len, reverse=True))) \
        if mem else None
    ref = re.compile(r'^\w+ = \("Pickle", \d+\)$')

    def as_text(line):
        return pat.sub(lambda m: '"%s"' % mem[m.group(1)], line) if pat else line

    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        old = a[i1:i2]
        for k, line in enumerate(b[j1:j2]):
            if ref.match(line) or (not line.strip() and op == "insert"):
                kinds["refs"] += 1
            elif op == "replace" and i2 - i1 == j2 - j1 and as_text(line) == old[k]:
                kinds["rename"] += 1
            else:
                kinds["other"] += 1
    return kinds


def sizes(up_root, new_root, lib, prod, model, enums_in_model):
    out = {}
    for s in ("Projection", "Data"):
        out[s] = count(lines(model_dir(up_root, lib, prod, model) / s / "__init__.py"),
                       lines(model_dir(new_root, lib, prod, model) / s / "__init__.py"))
    enums = (model_dir(new_root, lib, prod, model) / "enums.py" if enums_in_model
             else product_dir(new_root, lib, prod) / "enums.py")
    out["enums"] = count([], lines(enums))
    if enums_in_model:
        mem = members(enums)
        kinds = {"rename": 0, "refs": 0, "other": 0}
        for s in ("Projection", "Data"):
            k = classify(lines(model_dir(up_root, lib, prod, model) / s / "__init__.py"),
                         lines(model_dir(new_root, lib, prod, model) / s / "__init__.py"), mem)
            for x in kinds:
                kinds[x] += k[x]
        out["kinds"] = kinds
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
