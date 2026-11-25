"""Build the per-model results table from the check outputs.

    python tools/lean/results.py --root <lean tree> --report report.json --checks checks.jsonl
                                 --sizes sizes.jsonl --junit-up DIR --junit-lean DIR > RESULTS.md

``--junit-*`` hold ``ju_<side>_<lib>.xml`` from ``suite.sh``.  A test belongs to a model
when it is in the product's own module (``test_<product>_<cc>.py``) or carries the model's
name as its parameter (``[KLV_DE_S]``) in a shared module.
"""

import argparse
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from catalog import discover  # noqa: E402

SUFFIX = {"uslib": "us", "uklib": "uk", "delib": "de", "frlib": "fr", "jplib": "jp", "krlib": "kr"}


def outcomes(path):
    out = {}
    if not path.exists():
        return out
    for tc in ET.parse(path).iter("testcase"):
        key = tc.get("classname", "") + "::" + tc.get("name", "")
        res = "passed"
        for child in tc:
            if child.tag in ("failure", "error"):
                res = "failed"
            elif child.tag == "skipped":
                res = "skipped"
        out[key] = res
    return out


def belongs(key, lib, product, model):
    cls = key.split("::")[0].split(".")[-1]
    if cls == "test_%s_%s" % (product, SUFFIX[lib]):
        return True
    return re.search(r"\[(?:.*-)?%s(?:-.*)?\]$" % re.escape(model), key) is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--checks", nargs="+", required=True)
    ap.add_argument("--sizes", required=True)
    ap.add_argument("--junit-up", required=True)
    ap.add_argument("--junit-lean", required=True)
    a = ap.parse_args()
    rep = {r["model"]: r for r in json.load(open(a.report))}
    chk = {}
    for f in a.checks:
        for line in open(f):
            r = json.loads(line)
            chk[r["model"]] = r            # later files win (re-checks)
    sizes = {json.loads(l)["model"]: json.loads(l) for l in open(a.sizes)}
    ju = {}
    for side, d in (("up", a.junit_up), ("lean", a.junit_lean)):
        for lib in SUFFIX:
            ju[(side, lib)] = outcomes(pathlib.Path(d) / ("ju_%s_%s.xml" % (side, lib)))
    print("| model | generated | families | Projection +/- (lean) | enums | spec | full conversion Projection +/- | values exact | mismatches | tests lean (pass/fail/skip) | upstream | same outcome |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    tot = dict(values=0, mism=0, pas=0, fail=0, diff=0)
    for lib, prod, model in discover(a.root):
        r, c, s = rep.get(model, {}), chk.get(model, {}), sizes.get(model, {})
        counts = {}
        same = True
        for side in ("up", "lean"):
            o = {k: v for k, v in ju[(side, lib)].items() if belongs(k, lib, prod, model)}
            counts[side] = [sum(v == x for v in o.values()) for x in ("passed", "failed", "skipped")]
            counts[side + "_set"] = o
        same = counts["up_set"] == counts["lean_set"]
        lp = s.get("lean", {}).get("Projection", [0, 0])
        fp = s.get("full", {}).get("Projection", [0, 0])
        print("| %s | %s | %s | +%d/-%d | %d | %d | +%d/-%d | %s | %s | %d/%d/%d | %d/%d/%d | %s |" % (
            model, r.get("status", "?") if r.get("status") != "failed" else "failed: " + r.get("error", "")[:80],
            len(r.get("families", [])), lp[0], lp[1], s.get("lean", {}).get("enums", [0])[0],
            s.get("lean", {}).get("spec", [0])[0], fp[0], fp[1],
            c.get("values", "-"), c.get("mismatches", c.get("error", "-")),
            *counts["lean"], *counts["up"], "yes" if same else "NO"))
        tot["values"] += c.get("values", 0)
        tot["mism"] += c.get("mismatches", 0) or 0
        tot["pas"] += counts["lean"][0]
        tot["fail"] += counts["lean"][1]
        tot["diff"] += 0 if same else 1
    print()
    print("Totals: %(values)d values compared, %(mism)d mismatches; lean tests %(pas)d passed, "
          "%(fail)d failed; models whose test outcomes differ from upstream: %(diff)d." % tot)


if __name__ == "__main__":
    main()
