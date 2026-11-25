"""Derive a model's family map from the full conversion (the reference checkout).

The full conversion at 04d69db spelled every label as ``Family.MEMBER``, for arguments and
for policy attributes alike.  The map keeps what the lean rules need from it:

families     every IntEnum class of the product's ``enums.py`` with its members in order
             (names and values are reused as they are; nothing is renamed);
params       cell parameters typed by a family, by position (``{"cell": {"1": "Kind"}}``),
             from comparisons inside the cell and members passed at the call sites;
ref_returns  cells returning a member in the reference (policy attributes among them);
returns      the subset whose result is passed on as a cell argument -- in the lean text
             only these return a member, every other attribute stays a string;
member_refs  References whose value is a member and that are passed as an argument;
list_cells   cells whose upstream text returns a tuple where the reference returns a list;
hoists       cells that exist only in the reference (hoisted per-policy reads and
             re-spelled table reads), with the reference cells that call them -- the
             candidates for the optional ``hoists`` override;
spec         the product's ``spec.py`` (range declarations), verbatim.
"""

import ast
import json
import pathlib

from catalog import model_dir, product_dir
from engine import Typing
from modeltext import ModelText


def read_families(path):
    tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            members = []
            for st in node.body:
                if isinstance(st, ast.Assign) and isinstance(st.targets[0], ast.Name):
                    members.append([st.targets[0].id, ast.literal_eval(st.value)])
            out[node.name] = members
    return out


def _returns_list(fn_node, want):
    """True if a return statement of the cell builds a ``want`` ('list' or 'tuple')."""
    for r in ast.walk(fn_node):
        if isinstance(r, ast.Return) and r.value is not None:
            for v in ast.walk(r.value):
                if want == "list" and isinstance(v, (ast.List, ast.ListComp)):
                    return True
                if want == "tuple":
                    if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "tuple":
                        return True
                    if isinstance(v, ast.Tuple) and v is not r.value:
                        return True
                    if isinstance(v, ast.Tuple) and v is r.value:
                        return True
    return False


def derive(ref_root, upstream_root, lib, product, model):
    ref_dir = model_dir(ref_root, lib, product, model)
    families = read_families(product_dir(ref_root, lib, product) / "enums.py")
    fam_names = {F: [m for m, _ in ms] for F, ms in families.items()}
    ref = ModelText(ref_dir)
    typing = Typing(ref, fam_names, "ref")
    typing.derive_seq_returns()
    typing.derive_ref_returns()
    typing.solve(propagate=True)
    typing.derive_ref_returns()
    typing.solve(propagate=True)
    # member References: pickled names that are not classes, seen at typed positions
    member_refs = {}
    for sname, sp in ref.spaces.items():
        for name in sp.pickled_refs():
            if name not in families:
                member_refs[name] = sname
    mr = {}
    for fn in typing.fns.values():
        for node in ast.walk(fn.node):
            if isinstance(node, ast.Call):
                key, args = typing.call_args(fn, node)
                for pos, a in args:
                    F = typing.P.get(key, {}).get(pos) if key else None
                    if F and isinstance(a, ast.Name) and a.id in member_refs \
                            and a.id not in fn.params and a.id not in fn.bindings:
                        mr[(fn.space, a.id)] = F
    typing.MR = mr
    typing.solve(propagate=True)
    needed = typing.needed_returns()

    up_dir = model_dir(upstream_root, lib, product, model)
    up = ModelText(up_dir)
    list_cells = {}
    hoists = {}
    for sname, sp in ref.spaces.items():
        usp = up.spaces.get(sname)
        for cname, node in sp.cells.items():
            if usp is None or cname not in usp.cells:
                users = sorted(c for c, n in sp.cells.items() if c != cname and any(
                    isinstance(x, ast.Name) and x.id == cname for x in ast.walk(n)))
                hoists.setdefault(sname, {})[cname] = users
                continue
            if _returns_list(node, "list") and _returns_list(usp.cells[cname], "tuple") \
                    and not _returns_list(usp.cells[cname], "list"):
                list_cells.setdefault(sname, []).append(cname)

    # reference text of the hoisted cells and of the cells that use them, for the
    # optional ``hoists`` override
    hoist_sources = {}
    for sname, cells in hoists.items():
        sp = ref.spaces[sname]
        for cname, users in cells.items():
            for c in [cname] + users:
                hoist_sources.setdefault(sname, {})[c] = sp.src.segment(sp.cells[c])

    params = {}
    for (s, c), d in sorted(typing.P.items()):
        if d:
            names = ref.params((s, c))
            params.setdefault(s, {})[c] = {str(i): [F, names[i]] for i, F in sorted(d.items())}
    spec_path = product_dir(ref_root, lib, product) / "spec.py"
    return {
        "model": model, "lib": lib, "product": product,
        "families": families,
        "params": params,
        "ref_returns": _by_space(typing.ref_returns),
        "returns": _by_space(needed),
        "seq_returns": _by_space(typing.seq_returns),
        "member_refs": _by_space(mr),
        "list_cells": list_cells,
        "hoists": hoists,
        "hoist_sources": hoist_sources,
        "notes": sorted(set(typing.notes)),
        "spec": spec_path.read_text(encoding="utf-8") if spec_path.exists() else None,
    }


def _by_space(d):
    out = {}
    for (s, c), F in sorted(d.items()):
        out.setdefault(s, {})[c] = F
    return out


def write(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
