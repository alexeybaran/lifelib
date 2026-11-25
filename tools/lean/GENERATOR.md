# The lean conversion generator

`tools/lean/` turns the **upstream** text of the 57 regional `*_S` models (uslib, uklib,
delib, frlib, jplib, krlib) into the lean conversion: upstream text plus the one kind of
edit that carries almost all of the measured speed-up — labels passed as cell arguments
become members of a label family — and nothing else. Everything is generated; no
generated file is edited by hand. A rebase onto a new upstream is a re-run.

The conventions are the owner's "option B" (`GUIDE.md` states them for an author writing
a model by hand):

1. Families are **text-valued** enums, `enum.StrEnum`, each member's value upstream's own
   label text (`DEATH = "DEATH"`). A member equals, hashes and prints as its label, so text
   passed by a caller, text References and text defaults keep working, a table keyed by
   the label text finds the member, and a label of another family (or an int) fails
   upstream's own `raise ValueError(...)` guards. Python 3.11 is the floor for the model
   text.
2. Default arguments exactly as upstream has them (`kind=None`, `if kind is None:`, calls
   that omit the argument).
3. Cells that upstream returns as tuples stay tuples.
4. References and attribute cells keep upstream's text values; an attribute cell whose
   result is passed on as a cell argument converts it once (`Sex[v]`), which still equals
   and prints as the text.
5. Plain enum classes only: no metaclasses, no helper classes.
6. Where upstream checks a data label's text with its own `raise ValueError(...)` later
   than the lean text converts it, the converting cell checks first with upstream's
   labels and message (FIA_US_S, Dep_FR_S); otherwise an unknown label raises `KeyError`
   at the conversion, upstream's error type where upstream fails on a table lookup.

## Running it

```sh
# 0. once: derive the family maps from the full conversion (committed; re-run only if the
#    reference changes)
python tools/lean/lean.py extract --ref <checkout of the full conversion, 04d69db> \
                                  --base <checkout of upstream v0.17.3>

# 1. generate: read pristine upstream text, write the lean tree
python tools/lean/lean.py generate --upstream <pristine upstream checkout> --out <tree> \
                                   [--models KLV_DE_S ...] [--report report.json]

# 2. check (modelx with the S4 module-export change on PYTHONPATH)
python tools/lean/check.py      --upstream <pristine upstream> --out <tree> KLV_DE_S ...
python tools/lean/copycheck.py  --upstream <pristine upstream> --out <tree> \
                                --modelx <folder holding modelx> KLV_DE_S ...
tools/lean/runtests.sh <tree> delib kapitallebensversicherung KLV_DE_S
python tools/lean/diffsize.py   --upstream <pristine upstream> --out <tree> \
                                [--ref <full conversion> --base <v0.17.3>]
```

`--upstream` must be a pristine checkout (the generator always starts from upstream text,
so re-running over an already generated tree is safe). `--out` is usually the branch
checkout, itself cut from the same upstream commit, so `git diff <upstream>` on the branch
is the lean conversion.

`generate` writes, per model: `<Model>/Projection/__init__.py` (and `Data` when it needs
a family), `<Model>/enums.py`, `<Model>/_data/iospecs.py`, `<Model>/_data/data.pickle`,
the `enums` Reference in `<Model>/__init__.py`, the product's `spec.py`; and per library
the test edits (the model's `tests/test_<product>_<cc>.py` from upstream's, the
convention test of the model folder). It reports failures per model (first error) and exits non-zero if any model
failed.

`check.py` reads the upstream and the lean model with modelx in one process and compares
every public no-argument cell of `Data` and of `Projection[p]` for every point `p` of the
shipped `model_point_table`: frames and series with `check_exact=True` (index, columns and
dtypes included), floats bit for bit, a tuple only equal to a tuple, a member equal to the
label it stands for (its value), and the
same exception where upstream raises (for an error inside a formula this compares
modelx's `FormulaError`, not the inner message; the invalid-label checks in RESULTS.md
compare the inner error line).

## The rules, in the generator's terms

The family map of each model (`reference/<lib>/<Model>.json`) is derived from the full
conversion (`refmap.py`). Family and member names are the full conversion's, never
invented; the member values of the reference (integers) are not used: each value is the
label text.

* **families** — the product's enum classes of the full conversion.
* **typed parameter** — a cell parameter, by position, that the full conversion compares
  with members or that its callers pass members to. At generate time the types also
  propagate through the upstream text: a typed value passed to another cell types that
  parameter, and a parameter passed on to a typed position is typed.
* **scopes** — a comprehension's variables are local to it (as in Python), so `k` in one
  comprehension and `k` in another are different locals.
* **label site** — a string constant where a typed value is expected: an argument at a
  typed position, an operand of `==`, `!=`, `in`, `not in` against a typed value
  (membership tuples included), a source of a local that reaches a typed position
  (`for k in ("DEATH", "LAPSE")`), a value returned by a member-returning cell.

| rule | what the generator does |
|---|---|
| K1 | every label site becomes `Family.MEMBER` (short spelling). Nothing else of upstream's text changes: a typed value used as a table key, a column label, in an f-string or compared with text read from data stays as upstream writes it (the member *is* that text); defaults (`kind=None`, `weighting="count"`), `is None` tests and calls that omit the argument stay. A label *computed* from text at a typed position (`"comm_yr%d" % y`, `"surgery_rate_" + cause`) is looked up by name, `Family[expr]`. A cell that returns a sequence of labels whose elements are passed on (`opt_legs()` in RILA_US_S) returns a tuple of members. |
| attributes | a policy-attribute cell returns `Family[...]` of its upstream value **only** if its result is passed on as a cell argument (`sex(life)` in Rente_FR_S); every other attribute stays as upstream writes it; upstream's `raise ValueError("invalid ...")` checks stay, table loaders are upstream's. Families used only by attributes are not emitted. |
| References | a Reference holding a label keeps upstream's text (`tariff_table_sex = "F"`); it equals the member. |
| tuples | upstream's tuples stay (no K2). `reference/*.json` still lists the full conversion's `list_cells`; the generator ignores them. |
| None members | a member of the reference that upstream never spells and that stood for a `None` default (`Kind.ALL`) is not emitted. |
| K3 | the product's `spec.py` of the full conversion is written unchanged, with a two-line note that its line numbers refer to that text. |
| K4 | nothing to apply: the approved fixes (US mortality caps `min(q, 1.0)`, VA `rb_pp` `ratchet`, the Obseques and DIA validation fixes) are in upstream text since v0.17.3. |
| enums | `enums.py` in the model folder holds only the families the lean text spells, as `StrEnum` classes. It is stored with the model as a modelx `ModuleData` (spec id 1, `enums = ("IOSpec", 1)` in the model `__init__.py`); each space that spells a family gets `Family = ("Pickle", n)`, and `_data/data.pickle` maps `n` to the persistent id `("ModuleAttr", 1, "Family")`, which modelx (S4) resolves against the module loaded from the folder. No lifelib import is involved. |
| invalid labels | a label converted by `Family[...]` that is not a member raises `KeyError` there. Where upstream checks that text later with its own `raise ValueError(...)` (FIA_US_S `credit_method`/`glwb_basis`, Dep_FR_S's cause table), `overrides/<Model>.toml` puts upstream's check, with upstream's labels and message, in the converting cell ahead of the conversion (the error moves to that cell). Where upstream fails on a table lookup instead (CI_UK_S, Endowment_JP_S, LTC_JP_S) the error type is upstream's and the message differs; accepted. |
| not generated | `uslib/tests/_released`, the full conversion's `sample.py`, the DV01 example. |

Docstrings and comments are never edited.

### Tests

Upstream's tests run unchanged against the lean text: members equal their labels, so
calls with text labels, omitted defaults, comparisons with text and tuple assertions
behave as upstream. The generator writes each model's own test module from upstream's
with only these edits:

* a product test that lists the model folder's files also lists `enums.py` (and the two
  `_data` files where the listing is recursive); `overrides/VA_KR_S.toml` does the same
  for a listing the generic edit does not match.
* `overrides/_libraries.toml`: the convention test `test_model_folder_holds_formulas_only`
  allows `enums.py` and the two `_data` files.

## Overrides

`overrides/<Model>.toml` (optional; most models have none) and `overrides/_libraries.toml`.
Every entry carries a comment saying why. Keys:

```toml
[params.Projection.cell]       # type ("Family") or untype ("") a parameter by position
"1" = "Kind"
[returns.Projection]           # a cell returns a member (or "" for not)
sex = "Sex"
[labels.Family]                # a label that is not spelled like its member; the
"10yr" = "Y10"                 #   member's value is still the label ("10yr")
[none_member]                  # which member stood for a None default (not emitted)
Kind = "ALL"
[hoists]                       # OFF by default: adopt hoisted cells of the full conversion
Projection = ["cost_row"]      # inserts the helper and the reference text of its users
[[replace]]                    # exact text replacement in upstream text before the rewrite
space = "Projection"
old = "..."
new = "..."
[[tests.replace]]              # exact replacement in a test module after the test edits
file = "test_x.py"
optional = true                # absent text is not an error (e.g. on another upstream)
old = "..."
new = "..."
```

`hoists` is the hook for the next step: when the compiler reports a per-step read left on
pandas, list the reference helper here (`reference/.../<Model>.json`, key `hoists`, names
each helper and the cells that use it). Attribute families inside the adopted text are
spelled back as upstream strings.

## Rebasing onto a new upstream

1. Check out the new upstream commit (pristine) and cut the new branch from it.
2. `python tools/lean/lean.py generate --upstream <new> --out <branch> --report r.json`.
3. Each failure names the first problem, for example a new label that is not a member
   (`label 'X' is not a member of Kind`), a typed parameter whose upstream caller now
   passes something else, or an override replacement that no longer matches. Fix it in
   the overrides (or add the member to the reference map's family, with a comment), never
   in the generated files, and re-run.
4. Run `check.py`, `copycheck.py`, the tests and `diffsize.py`.

Upstream v0.17.3 → main (20d4dae) changed one of the 57 models, IP_UK_S (its two vector
cells became tuples, with a test asserting immutability); the lean text keeps the tuples
and the test as upstream. No table CSV of the 57 changed in that range.
