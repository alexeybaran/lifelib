# The lean conversion generator

`tools/lean/` turns the **upstream** text of the 57 regional `*_S` models (uslib, uklib,
delib, frlib, jplib, krlib) into the lean conversion: upstream text plus the one kind of
edit that carries almost all of the measured speed-up — labels passed as cell arguments
become IntEnum members — and nothing else. Everything is generated; no generated file is
edited by hand. A rebase onto a new upstream is a re-run.

Standard library only for the generator (`ast`, `pickle`, `tomllib`); modelx is needed
only by the checks.

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
the mechanical test edits (the model's `tests/test_<product>_<cc>.py`, the
`model_enums` helper in `tests/<cc>_registry.py`, the convention test of the model
folder). It reports failures per model (first error) and exits non-zero if any model
failed.

`check.py` reads the upstream and the lean model with modelx in one process and compares
every public no-argument cell of `Data` and of `Projection[p]` for every point `p` of the
shipped `model_point_table`: frames and series with `check_exact=True` (index, columns and
dtypes included), floats bit for bit, a member equal to the label it stands for, and the
same exception where upstream raises (for an error inside a formula this compares
modelx's `FormulaError`, not the inner message; the invalid-label checks in RESULTS.md
compare the inner error line).

## The rules, in the generator's terms

The family map of each model (`reference/<lib>/<Model>.json`) is derived from the full
conversion (`refmap.py`). Family and member names and member values are the full
conversion's, never invented.

* **families** — the product's IntEnum classes of the full conversion.
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
| K1 | every label site becomes `Family.MEMBER` (short spelling); a typed `kind=None` default loses its default when the family has exactly one member that upstream never spells (`Kind.ALL`): `kind is None` becomes `kind == Kind.ALL` and a call that omits the argument passes `Kind.ALL`. A typed label default (`weighting="count"`) is dropped the same way and omitting calls pass the member. A *value use* of a typed value — a table key, a column label, a comparison with a string read from data, anything that is not a comparison with a label, a typed argument or a returned member — is spelled `x.name`, which is the upstream string, so upstream tables and loaders are untouched. A label *computed* from text at a typed position (`"comm_yr%d" % y`, a loop over a table's string index) is looked up by name, `Family[expr]`. A cell that returns a sequence of labels whose elements are passed on (`opt_legs()` in RILA_US_S) returns members, and its loops are typed. |
| attributes | a policy-attribute cell returns `Family[...]` of its upstream value **only** if its result is passed on as a cell argument (`sex(life)` in Rente_FR_S); every other attribute stays a string, upstream's `raise ValueError("invalid ...")` checks stay, table loaders are upstream's. Families used only by attributes are not emitted. |
| References | a Reference holding a label that is passed as an argument holds the member (`tariff_table_sex`, pickled as `Sex(1)`). |
| K2 | the cells listed (`list_cells`: those whose upstream returns a tuple where the full conversion returns a list, plus overrides) build lists: `tuple(g)` → `[g]`, `(a, b)` → `[a, b]`, `(x,) * n` → `[x] * n`, and the same in the locals they return. `return a, b, c` stays a tuple of vectors. |
| K3 | the product's `spec.py` of the full conversion is written unchanged, with a two-line note that its line numbers refer to that text. |
| K4 | nothing to apply: the approved fixes (US mortality caps `min(q, 1.0)`, VA `rb_pp` `ratchet`, the Obseques and DIA validation fixes) are in upstream text since v0.17.3. |
| enums | `enums.py` in the model folder holds only the families the lean text spells. It is stored with the model as a modelx `ModuleData` (spec id 1, `enums = ("IOSpec", 1)` in the model `__init__.py`); each space that spells a family gets `Family = ("Pickle", n)`, and `_data/data.pickle` maps `n` to the persistent id `("ModuleAttr", 1, "Family")`, which modelx (S4) resolves against the module loaded from the folder. No lifelib import is involved. |
| invalid labels | a label converted by `Family[...]` that is not a member raises `KeyError` there. Where upstream checks that text later with its own `raise ValueError(...)` (FIA_US_S `credit_method`/`glwb_basis`, Dep_FR_S's cause table), `overrides/<Model>.toml` puts upstream's check, with upstream's labels and message, in the converting cell ahead of the conversion (the error moves to that cell). Where upstream fails on a table lookup instead (CI_UK_S, Endowment_JP_S, LTC_JP_S) the error type is upstream's and the message differs; accepted. |
| not generated | `uslib/tests/_released`, the full conversion's `sample.py` (a compiler-harness file identical in all 57 products that calls `collect_outputs()`, which no `*_S` model defines, and imports the compiler's `exported` package), the DV01 example. |

Docstrings and comments are never edited, so a docstring may still name a label as a
string.

### Tests

The test edits are mechanical and generated (`testedit.py`):

* a call `x.cell(..., "LABEL")` at a typed position passes `Family.LABEL`; a call that
  omits a dropped `kind=None` argument passes the `None` member; a member-returning cell
  compared with a label is compared with the member; label loops feeding typed arguments
  loop over members. A label that is not a member (a test of the invalid-value error) is
  left as it is — it still raises. A label a test holds in a parameter or a loop variable
  that it also uses as a string (a dict key) is looked up at the call, `Kind[kind]`.
  Comparisons with a member-returning cell or a member Reference (`Projection.x`,
  `space.refs["x"]`, element-wise in tuple comparisons) compare with the member.
* a product test that lists the model folder's files also lists `enums.py` (and the two
  `_data` files where the listing is recursive).
* a function a test installs as a formula (`model.Projection.wd_pp.formula = f`) gets the
  same K1 edits as the model text; a loop over a cell that returns members
  (`for leg in p.opt_legs()`) holds members, so its uses as dict keys read `leg.name`.
* `overrides/_libraries.toml`: uslib's S-vs-SEC twin identity (`sec_support._twin_lines`)
  passes a lean S model's members to the SEC twin, which is upstream text, as their labels
  (the `ALL` members as `None`), and compares the S results the same way.
* `overrides/_libraries.toml`: uslib's SEC test modules (`*_sec.py`) call the S twins
  with upstream's string labels. `sec_support` gains a view, active only when the
  caller is SEC test code: label arguments of a lean S cell become members of that
  model's own stored `enums` module (an omitted or `None` `kind` becomes `ALL`),
  members in results read back as labels (`ALL` as `None`), and the family classes and
  `enums` module are left out of the References those tests compare. The typed
  parameters are read from the S formulas, for the whole space at once. SEC models and
  S model text are not touched.
* the families come from the model folder: `tests/<cc>_registry.py` gains `model_enums(name,
  *families)`, which loads `<model>/enums.py` from the model folder; each edited test
  module gains `from <cc>_registry import model_enums` and one assignment.
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
[labels.Family]                # a label that is not spelled like its member
"10yr" = "Y10"
[none_member]                  # which member stands for a None default
Kind = "ALL"
[list_cells]                   # K2 cells beyond the reference's
Projection = ["sick_cohorts"]
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
cells became tuples, with a test asserting immutability); `overrides/IP_UK_S.toml` lists
the two cells under `list_cells` (a no-op on v0.17.3) and adjusts that test
(`optional`, absent on v0.17.3). No table CSV of the 57 changed in that range.
