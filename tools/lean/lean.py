"""Generate the lean conversion of the regional ``*_S`` models from upstream text.

    python tools/lean/lean.py extract  --ref <full conversion checkout> --base <upstream v0.17.3>
    python tools/lean/lean.py generate --upstream <pristine upstream checkout> --out <tree>
                                       [--models KLV_DE_S ...] [--no-tests]
    python tools/lean/lean.py diffstat --upstream <pristine upstream checkout> --out <tree>

``extract`` writes ``tools/lean/reference/<lib>/<Model>.json`` (the family map of the full
conversion; run once, it is committed).  ``generate`` reads upstream text, the reference
map and ``tools/lean/overrides/<Model>.toml`` and writes the lean model folders, the
products' ``spec.py`` and the mechanical test edits into ``--out``.  See GENERATOR.md.
"""

import argparse
import ast
import json
import pathlib
import shutil
import sys
import tomllib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from catalog import discover, model_dir, product_dir  # noqa: E402
from emit import IOSPECS, MODEL_REF, append_refs, data_pickle, enums_module  # noqa: E402
from engine import GenerationError  # noqa: E402
from modeltext import ModelText  # noqa: E402
from rewrite import Rewriter  # noqa: E402
import testedit  # noqa: E402

REFERENCE = HERE / "reference"
OVERRIDES = HERE / "overrides"
REGISTRY = {"uslib": "us_registry", "uklib": "uk_registry", "delib": "de_registry",
            "frlib": "fr_registry", "jplib": "jp_registry", "krlib": "kr_registry"}
SUFFIX = {"uslib": "us", "uklib": "uk", "delib": "de", "frlib": "fr", "jplib": "jp", "krlib": "kr"}
SPEC_NOTE = ("# Range declarations of the full conversion (K3), unchanged; the line numbers in\n"
             "# the comments below refer to that conversion's text at 04d69db.\n")


FILE_SET = '"__init__.py", "_system.json"}'
FILE_SET_LEAN = '"__init__.py", "_system.json", "enums.py"}'
FILE_SET_RGLOB = 'model_files(MODEL_DIR) == {"__init__.py", "_system.json"}'
FILE_SET_RGLOB_LEAN = ('model_files(MODEL_DIR) == {"__init__.py", "_system.json", "enums.py",\n'
                       '                                     "iospecs.py", "data.pickle"}')


def ref_path(lib, model):
    return REFERENCE / lib / (model + ".json")


def load_overrides(model):
    path = OVERRIDES / (model + ".toml")
    if not path.exists():
        return {}
    with path.open("rb") as f:
        ov = tomllib.load(f)
    # "" removes an entry (TOML has no null)
    for key in ("params", "returns"):
        for s, cells in ov.get(key, {}).items():
            for c, v in cells.items():
                if isinstance(v, dict):
                    cells[c] = {k: (None if x == "" else x) for k, x in v.items()}
                elif v == "":
                    cells[c] = None
    return ov


def cmd_extract(args):
    from refmap import derive, write
    for lib, prod, model in discover(args.ref):
        if args.models and model not in args.models:
            continue
        data = derive(args.ref, args.base, lib, prod, model)
        write(ref_path(lib, model), data)
        print("extracted", model)


def apply_replacements(texts, ov, model):
    for r in ov.get("replace", []):
        s = r["space"]
        if texts[s].count(r["old"]) != 1:
            raise GenerationError("%s: override replacement not found exactly once in %s: %r"
                                  % (model, s, r["old"][:60]))
        texts[s] = texts[s].replace(r["old"], r["new"])
    return texts


def generate_model(upstream, out, lib, prod, model, tests=True):
    refmap = json.loads(ref_path(lib, model).read_text(encoding="utf-8"))
    ov = load_overrides(model)
    src_dir = model_dir(upstream, lib, prod, model)
    up = ModelText(src_dir)
    texts = {s: sp.text for s, sp in up.spaces.items()}
    texts = apply_replacements(texts, ov, model)
    if ov.get("hoists"):
        import hoist
        keep = {F for cells in refmap["params"].values() for d in cells.values() for F, _ in d.values()}
        texts = hoist.adopt(texts, up, refmap, ov["hoists"], keep)
    m = ModelText(src_dir, texts=texts)
    rw = Rewriter(m, refmap["families"], refmap, ov)
    new = rw.run()

    # References: classes spelled in each space, then member References
    used = {s: set(fs) for s, fs in rw.used.items()}
    member_refs = {}
    for s, d in refmap.get("member_refs", {}).items():
        for name, F in d.items():
            member_refs[(s, name)] = F
            used.setdefault(s, set())
    keep = set().union(*used.values()) if used else set()
    keep |= set(member_refs.values())
    order = [F for F in refmap["families"] if F in keep]
    ids = {}
    nxt = 2
    for F in order:
        ids[F] = nxt
        nxt += 1
    entries = {ids[F]: ("class", F) for F in order}
    for s in m.spaces:
        refs = [(F, ids[F]) for F in order if F in used.get(s, set())]
        for (rs, name), F in sorted(member_refs.items()):
            if rs != s:
                continue
            node = m.spaces[s].refs[name]
            label = ast.literal_eval(node.value)
            members = dict(refmap["families"][F])
            if label not in members:
                raise GenerationError("%s: Reference %s = %r is not a %s member" % (model, name, label, F))
            entries[nxt] = ("member", F, members[label])
            seg_old = m.spaces[s].src.segment(node)
            seg_new = '%s = ("Pickle", %d)' % (name, nxt)
            if new[s].count(seg_old) != 1:
                raise GenerationError("%s: cannot place Reference %s" % (model, name))
            new[s] = new[s].replace(seg_old, seg_new)
            nxt += 1
        new[s] = append_refs(new[s], refs)

    dst = model_dir(out, lib, prod, model)
    for s, text in new.items():
        ast.parse(text)
        (dst / s / "__init__.py").write_text(text, encoding="utf-8")
    init = up.init_text
    for f in ("enums.py",):
        p = dst / f
        if p.exists():
            p.unlink()
    data_dir = dst / "_data"
    if data_dir.exists():
        shutil.rmtree(data_dir)
    if keep:
        (dst / "enums.py").write_text(enums_module(model, refmap["families"], keep), encoding="utf-8")
        data_dir.mkdir()
        (data_dir / "iospecs.py").write_text(IOSPECS, encoding="utf-8")
        (data_dir / "data.pickle").write_bytes(data_pickle(entries))
        init = init.rstrip("\n") + MODEL_REF
    (dst / "__init__.py").write_text(init, encoding="utf-8")
    spec = refmap.get("spec")
    spec_path = product_dir(out, lib, prod) / "spec.py"
    if spec:
        spec_path.write_text(SPEC_NOTE + spec, encoding="utf-8")

    report = {"model": model, "families": order, "notes": rw.notes,
              "none_member": rw.none_member, "tests": {}}
    if tests:
        report["tests"] = edit_tests(upstream, out, lib, prod, model, rw, refmap, ov, order)
    return report


def edit_tests(upstream, out, lib, prod, model, rw, refmap, ov, order):
    """Apply the mechanical test edits to the model's own test module(s)."""
    T = rw.typing
    typed, pnames = {}, {}
    for (s, c), d in T.P.items():
        if s == "Projection" and d:
            typed[c] = dict(d)
            pnames[c] = m_params(rw.model, (s, c))
    returns = {c: F for (s, c), F in T.R.items() if s == "Projection"}
    none_member = {}
    for (s, c), d in T.P.items():
        if s != "Projection" or (s, c) not in T.fns:
            continue
        defaults = rw.model.defaults((s, c))
        names = rw.model.params((s, c))
        for pos, F in d.items():
            dflt = defaults.get(names[pos])
            if isinstance(dflt, ast.Constant) and dflt.value is None:
                none_member.setdefault(c, {})[pos] = rw.default_member[((s, c), pos)]
            elif ((s, c), pos) in rw.default_member:
                none_member.setdefault(c, {})[pos] = rw.default_member[((s, c), pos)]
    fams = {F: [m for m, _ in ms] for F, ms in refmap["families"].items()}
    tests_dir = pathlib.Path(out) / "lifelib" / "libraries" / lib / "tests"
    up_tests = pathlib.Path(upstream) / "lifelib" / "libraries" / lib / "tests"
    out_report = {}
    names = ov.get("test_files", ["test_%s_%s.py" % (prod, SUFFIX[lib])])
    for name in names:
        src = up_tests / name
        if not src.exists():
            out_report[name] = "missing"
            continue
        text = src.read_text(encoding="utf-8")
        mrefs = {n: F for (s, n), F in T.MR.items() if s == "Projection"}
        ed = testedit.TestEditor(text, typed, returns, fams, none_member, mrefs)
        ed.pnames = pnames
        ed.seq_returns = {c: F for (s, c), F in T.seq_returns.items() if s == "Projection"}
        text = ed.run()
        for r in ov.get("tests", {}).get("replace", []):
            if r.get("file", name) != name:
                continue
            if text.count(r["old"]) != 1:
                if r.get("optional") and text.count(r["old"]) == 0:
                    continue
                raise GenerationError("%s: test replacement not found exactly once: %r" % (name, r["old"][:60]))
            text = text.replace(r["old"], r["new"])
            ed.count += 1
            for F in r.get("families", []):
                ed.used.add(F)
        if order and FILE_SET_RGLOB in text:
            # model_files() walks the folder recursively: the two IOSpec files appear too
            text = text.replace(FILE_SET_RGLOB, FILE_SET_RGLOB_LEAN)
            ed.count += 1
        if order and FILE_SET in text:
            # the model folder now also holds enums.py (S4 recipe)
            text = text.replace(FILE_SET, FILE_SET_LEAN)
            ed.count += text.count(FILE_SET_LEAN)
        if ed.used:
            fam_list = [F for F in order if F in ed.used]
            text = testedit.add_import(text, REGISTRY[lib], model, fam_list)
        (tests_dir / name).write_text(text, encoding="utf-8")
        out_report[name] = {"edits": ed.count, "families": sorted(ed.used), "unhandled": ed.unhandled,
                           "kept_invalid": ed.kept}
    return out_report


def m_params(model, key):
    return model.params(key)


def ensure_registry_helper(upstream, out, lib):
    reg = REGISTRY[lib] + ".py"
    src = pathlib.Path(upstream) / "lifelib" / "libraries" / lib / "tests" / reg
    dst = pathlib.Path(out) / "lifelib" / "libraries" / lib / "tests" / reg
    text = src.read_text(encoding="utf-8")
    if "def model_enums" not in text:
        text = text.rstrip("\n") + "\n" + testedit.REGISTRY_HELPER
    dst.write_text(text, encoding="utf-8")


def library_test_edits(upstream, out, libs):
    """The shared test edits of ``overrides/_libraries.toml`` (convention tests)."""
    path = OVERRIDES / "_libraries.toml"
    if not path.exists():
        return
    with path.open("rb") as f:
        ov = tomllib.load(f)
    texts = {}
    for r in ov.get("replace", []):
        for rel in r["files"]:
            if rel.split("/")[0] not in libs:
                continue
            if rel not in texts:
                src = pathlib.Path(upstream) / "lifelib" / "libraries" / rel
                texts[rel] = src.read_text(encoding="utf-8")
            if texts[rel].count(r["old"]) != 1:
                raise GenerationError("%s: library test replacement not found exactly once" % rel)
            texts[rel] = texts[rel].replace(r["old"], r["new"])
    for rel, text in texts.items():
        dst = pathlib.Path(out) / "lifelib" / "libraries" / rel
        dst.write_text(text, encoding="utf-8")


def cmd_generate(args):
    reports = []
    libs = set()
    for lib, prod, model in discover(args.upstream):
        if args.models and model not in args.models:
            continue
        if not ref_path(lib, model).exists():
            print("no reference map for", model)
            continue
        try:
            r = generate_model(args.upstream, args.out, lib, prod, model, tests=not args.no_tests)
            r["status"] = "generated"
            libs.add(lib)
        except GenerationError as e:
            r = {"model": model, "status": "failed", "error": str(e)}
        reports.append(r)
        print(model, r["status"], r.get("error", ""), r.get("families", ""))
    if not args.no_tests:
        for lib in sorted(libs):
            ensure_registry_helper(args.upstream, args.out, lib)
        library_test_edits(args.upstream, args.out, libs)
    if args.report:
        pathlib.Path(args.report).write_text(json.dumps(reports, indent=1), encoding="utf-8")
    return 0 if all(r["status"] == "generated" for r in reports) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("--ref", required=True)
    e.add_argument("--base", required=True)
    e.add_argument("--models", nargs="*")
    g = sub.add_parser("generate")
    g.add_argument("--upstream", required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--models", nargs="*")
    g.add_argument("--no-tests", action="store_true")
    g.add_argument("--report")
    args = ap.parse_args(argv)
    if args.cmd == "extract":
        return cmd_extract(args)
    return cmd_generate(args)


if __name__ == "__main__":
    sys.exit(main())
