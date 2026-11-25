# Review A of the lean conversion (branch `r4/l1-lean` at b6aad67 vs upstream 20d4dae)

Independent review. Everything below was run here: Python 3.13, pandas 3.0, live modelx
from branch `r4/modelx-integration`; upstream text in a worktree at 20d4dae. No compiler
was available in this stack, so **compiled speed and memory were not measured**; every
statement about them is an inference and is marked as such.

What I confirmed of the stated properties:

* `lean.py generate` on pristine 20d4dae reproduces the committed tree byte for byte
  (57/57 generated, `diff -r` empty). It needs only the committed `reference/*.json`.
* `check.py` on nine models from all six libraries (IP_UK_S, CI_UK_S, RLV_DE_S, Dep_FR_S,
  Rente_FR_S, Annuity_JP_S, Pension_KR_S, FIA_US_S, RILA_US_S): 1,261,736 values, 0
  mismatches. Two uklib product test modules: 99 passed.
* The equality is "a member counts as equal to its label" (`check.py: norm`). Cells that
  returned text upstream and return a member now are reported equal (section 3, D5).
* `check.py` compares only no-argument cells and only the outer `FormulaError`; it
  cannot see differences in cells that take a label, which is where they are.

## 1. Kinds of change (counts over the 57 models)

Diff against upstream: `Projection` +2,723/−2,336 in 56 models (Term_US_S untouched; no
`Data` space changed), `enums.py` +1,577 (56 files, 189 families, 842 members), `spec.py`
+597 (57 files) = 7,233. Not in that figure: 56 model `__init__.py` (+263), 112 `_data`
files (56 binary pickles), tests +2,919/−2,465 in 69 files, `tools/lean` +14,949.
Counts are from an AST/line classifier over all 57, hunks read by hand in IP_UK_S,
Rente_FR_S, LTC_JP_S, RLV_DE_S, FIA_US_S (plus parts of CI_UK_S, Child_KR_S, BU_DE_S).
The generator's categories match the diff; the brief's "hoisted pandas reads" do not
occur (`hoists` is off, no override uses it, 0 new cells).

| kind (generator's name) | sites | models | before → after |
|---|---|---|---|
| K1 label → member | 2,357 spellings, 2,029 lines that change in nothing else | 56 | `claims(t, "DEATH")` → `claims(t, Kind.DEATH)`; `if timing == "BEF_DECR":` → `if timing == PolTiming.BEF_DECR:` |
| K1 `None` default → `ALL` member | 68 signatures, 62 comparisons, 65 calls that now pass it | 54 | `def claims(t, kind=None):` / `if kind is None:` / `claims(t)` → `def claims(t, kind):` / `if kind == Kind.ALL:` / `claims(t, Kind.ALL)` |
| K1 value use `.name` | 56 | 20 | `.loc[(table_sex, gen, x), ...]` → `.loc[(table_sex.name, gen, x), ...]` |
| K1/attributes by-text lookup `Family[...]` | 25 (19 read from data, 3 built in code, 3 `Smoker[smoker2()]`) | 12 | `return v` → `return Sex[v]`; `"comm_yr%d" % y` → `ChargeLine["comm_yr%d" % y]` |
| References holding a member | 2 | 2 | `tariff_table_sex = "F"` → `tariff_table_sex = ("Pickle", 5)` |
| K2 tuple → list | 13 cells, 19 lines | 5 (BU_DE_S 6, IP_UK_S 2, Medical_JP_S 2, Pflege_DE_S 2, VA_KR_S 1) | `return tuple(f(z) for z in zs)` → `return [f(z) for z in zs]` |
| invalid-label checks moved | 9 lines, 3 cells | 2 | `return model_point()["glwb_basis"]` → `v = ...; if v not in ("single", "joint"): raise ValueError(...); return GlwbBasis[v]` |
| enums wiring | 189 `Family = ("Pickle", n)` lines (380 with blanks), `enums = ("IOSpec", 1)`, `iospecs.py`, `data.pickle` | 56 | new |
| K3 range declarations | 57 `spec.py` | 57 | new: `{'cells_param_size': {'t': 636, 'z': 626}}` |

## 2. Convenience for the actuary

| kind | written unprompted? | harder to read / easier to get wrong | could stay upstream's |
|---|---|---|---|
| label → member | Plausibly, once told. Reads well. | Which family goes with which cell is nowhere in the text: `Kind`, `Claim` and `ClaimKind` name the same idea in 44/8/5 models, `PolTiming`/`PolsTiming` in 42/5. 249 of 842 members are lower case (`GlwbBasis.single`, `PrevParam.prev_ceil`) beside upper-case ones. A wrong family is accepted silently (D1). | Yes, if the compiler interns literals (section 5). |
| `ALL` for `None` | No. `claims(t)` is the natural total and is now a `TypeError`. | `ALL` is not "all": in LTC_JP_S `Kind.ALL` sums LUMP+ANNUITY+DEMENTIA and leaves LAPSE out. Rente_FR_S had a real label `"ALL"` (`AnnuityKind.ALL`) and gains a second, invented `Kind.ALL`. A natural `for k in Kind` now includes the total. Docstrings still say "the total when kind is omitted". | Yes: keep the default (`kind=Kind.ALL` if a member is needed); 65 call sites stay. |
| `.name` | No. | The author must know, per use, whether a parameter is "compared" or "used as a value"; forgetting `.name` in a table key gives a `KeyError` on `<Sex.M: 0>`, and a text label passed in gives `AttributeError` (D3). | Yes with text-valued members. |
| `Family[...]` | Only with a guide. | `sex()` returns a member in 6 models and text in the others, by a rule the reader cannot see ("only if the result is passed as a cell argument"). `sex() == "M"` is silently `False` in those six; formatting gives `0`/`1` (D5). | Yes: attributes can stay text. |
| member in a Reference | No. | The model text no longer shows the value: `("Pickle", 5)`. The docstring still says the shipped value is `"F"`; setting it that way fails (D4). | Yes. |
| tuple → list | Lists are what most actuaries write, but upstream chose tuples on purpose in 13 cells of 5 models, not only IP_UK_S. | Cached vectors become mutable again: one stray assignment corrupts later results with no error (D6). The IP_UK_S docstrings still say "tuple"; upstream's immutability test was replaced by `isinstance(v, list)`. | Yes; drop K2 unless the compiler cannot take a tuple of floats. |
| enums wiring | No; it cannot be typed by hand (binary pickle with persistent ids). | Released modelx 0.33.0 reads the lean model with warnings, sets every family to `None`, and every label cell then fails (D8). | — |
| `spec.py` | No. | Lives outside the model, keyed by parameter *name* for the whole model; its comments cite line numbers of a different text (`Projection:593` at 04d69db). Nothing in the model enforces the bounds (D9). | — |

Not updated by the conversion: the 57 `run.py` scripts, notebooks and prose that call
cells with text labels (D7).

## 3. Reliability: where lean and upstream differ in live modelx

`u`/`l` are upstream and lean models read with `mx.read_model`; `p = m.Projection[1]`;
`E = l.enums`. Errors are the inner error of the `FormulaError` unless noted.

| # | reproduction | upstream | lean |
|---|---|---|---|
| D1 wrong family, silent value | IP_UK_S `p.claims(5, E.PolTiming.BEF_DECR)` (upstream `"BEF_DECR"`) | `ValueError: invalid kind` | `0.9229…` (= BENEFIT) |
| | IP_UK_S `p.pols_if_at(5, E.Kind.DEATH)` | `ValueError: invalid timing` | `0.9481…` (= AFT_DECR) |
| | CI_UK_S `p.pols_if_at(5, E.BenefitKind.CHILD)` | `ValueError: invalid timing` | `0.9475…` |
| | IP_UK_S `p.claims(5, 0)`; `p.claims(5, True)` | `ValueError` | `0.9229…`; `0.0` (bool/int taken as members) |
| D2 upstream's own spelling | IP_UK_S `p.claims(5)` | `0.9229…` | `TypeError: missing a required argument: 'kind'` |
| | `p.claims(5, None)`; `p.claims(5, "BENEFIT")` | `0.9229…` both | `ValueError: invalid kind` both |
| | Rente_FR_S `p.cum_annuity_pp(12, "ALL")` | `5452.81` | `ValueError: invalid kind` |
| D3 text into a `.name` site | Rente_FR_S `p.mort_rate_at_age("F", 1950, 70)` | `0.005347685` | `AttributeError` (`table_sex.name`) |
| D4 Reference set as documented | Rente_FR_S `m.Projection.tariff_table_sex = "M"`; `p.taux_rente_tariff()` | `0.0373` | `AttributeError`; same for `"F"`, `"mix"` |
| | Child_KR_S `m.Projection.ref_sex = "F"`; `p.sa_notional_pp()` | `291074098.8` | `AttributeError` (`s.name`) |
| D5 attribute value changes type | Rente_FR_S `p.sex(1)`; `p.sex(1) in ("M","F","mix")`; `"{}".format(p.sex(1))` | `'M'`; `True`; `'M'` | `<Sex.M: 0>`; `False`; `'0'` |
| | FIA_US_S `p.credit_method()`, `p.glwb_basis()` | `'cap'`, `'single'` | members |
| D6 cached vector mutated | IP_UK_S `v = p.sick_cohorts(2); v[0] = 999.0; p.pols_sick(2)` | `TypeError` at the assignment; `0.000209…` | no error; `999.0001…` |
| | BU_DE_S `v = p.recov_rates(); v[0] = 0.99; p.recov_rate_mth_year()[0]` | `TypeError` | `0.3187…` |
| D7 shipped scripts | `python run.py` in each of the 57 product folders | 57 exit 0 | 8 fail: uslib fixed_indexed_annuity, variable_annuity; uklib critical_illness, with_profits; frlib obseques; jplib individual_annuity; krlib cancer, child. frlib rente_viagere exits 0 but prints `065 with reversion to 161` for `M65 … F61` |
| D8 released modelx | modelx 0.33.0 `read_model(IP_UK_S)`; `p.claims(5, m.enums.Kind.BENEFIT)` | works | warnings `unsupported persistent object`, `Kind` restored as `None`, then `AttributeError: 'NoneType' object has no attribute 'ALL'` |
| D9 longer projection | IP_UK_S point 1 with `entry_age=18`, `expiry_age=75`: `proj_len()` | `684` | `684`, same values live; but `spec.py` declares `t < 636` and no formula validates `expiry_age`. Compiled behaviour past the bound: not tested here. |
| D10 unknown / blank label in data | LTC_JP_S `grade_lump` = `""`, `"ALL"`, `"care4"`; Endowment_JP_S `sex` = `""` | attribute cell returns the text (`'nan'`, `'care4'`); users of it fail on the table lookup | attribute cell itself raises `KeyError`; other cells as upstream |
| | FIA_US_S `credit_method` = `""` (also with `alloc_indexed=0`) | `ValueError: invalid credit_method` in `credit_rate_on` | same `ValueError`, raised in `credit_method()` |

Inputs where I found **no** difference: blank/`nan`/`ALL`/lower-case/`0` in CI_UK_S `sex`
and `smoker`, blank Rente_FR_S `annuitant_sex`, blank LTC_KR_S `benefit_grade`, blank
FIA_US_S `glwb_basis` on a point without the rider (the result frames are equal; only
the attribute cell differs), a missing table key reached through `.name` (same
`KeyError`), an empty Dep_FR_S cause table (the added loop is a no-op). The stated
property "same error type on an unknown label" held in every data-boundary case tried.

D1 is the one that matters: upstream's `raise ValueError("invalid …")` guards, which stay
in the text, no longer guard, because any IntEnum member (or int, or bool) with the same
number passes. The tests rely on this: `model_enums()` loads `enums.py` a second time, so
test members are not the model's classes and match only by number. D2–D5 and D7 are one
fact seen from the caller's side: lean is not call-compatible with upstream.

Checked alternative (IP_UK_S, lean text, only `enums.py` changed to
`class Kind(StrEnum): BENEFIT = "BENEFIT" …`): `check.py` 44,422 values, 0 mismatches;
`claims(5, "BENEFIT")` works; `claims(5, PolTiming.BEF_DECR)` raises `ValueError` as
upstream. Text-valued members remove D1, the text half of D2, D3, D4, D5 and D7 without
touching a formula. Whether the compiler keeps its speed with them (it can number the
members at compile time) is for the compiler side to confirm.

## 4. Generic: can another author follow the conventions from one page?

| convention | rule on one page? | needs the generator? |
|---|---|---|
| enum module per model | The idea, yes. The mechanics, no: `enums.py` must be registered as `ModuleData`, each family assigned as a Reference in each space, and `data.pickle` written with persistent ids. That is done from a live session of the forked modelx or by `emit.py`, not by editing text. `PolTiming` is defined 42 times. | forked modelx or generator |
| family and member names | No. Names "are the full conversion's, never invented" (`reference/*.json` from a checkout that is not in this repository). There is no rule that yields `Kind` vs `Claim` vs `ClaimKind`, member case, or numbering. A member must be a Python identifier equal to the label, or `.name`/`Family[...]` break (`[labels]` exists for that and is unused). | a new model has no reference map |
| by-text lookup at the boundary | Partly. "Convert an attribute only if its result is passed as an argument; else leave text; put upstream's check before the lookup" is a whole-model data-flow property; the generator computes it by propagation, an author must trace it by hand and re-trace on every edit. | in practice yes |
| `.name` at value uses | Same data-flow question, per use. | in practice yes |
| `ALL` for `None` | Yes, mechanical. | no |
| range declarations | No. Each `spec.py` is a hand argument from product limits (`need_max 624 + … +12 margin`), not derivable by rule and not checked against the model. | no (copied, not generated) |

Is the generator needed after landing? It depends on which text is the source.

* If the lean text becomes the source that authors edit, the generator has no further
  job and should be dropped with its 14.9k lines; then the conventions must stand on a
  guide, and per the table three of six do not.
* If upstream keeps writing text labels (it did so in every commit up to 20d4dae), the
  lean text is a derived artefact, the generator is needed at every rebase, and it
  carries 22 override files and a frozen map of an external checkout. For a 58th model
  it cannot run until someone writes that model's family map.

Neither is comfortable. A conversion that is 57/57 automatic from upstream text is
evidence that the compiler could do the same analysis at compile time.

## 5. Size: renaming vs rewriting

Of the 2,708 added `Projection` lines (classifier; git counts 2,723 with file endings):

| part | added lines | share |
|---|---|---|
| pure rename (line differs only by `"X"` → `Family.X`) | 2,029 | 75% |
| `Family = ("Pickle", n)` Reference lines and blanks | 380 | 14% |
| `None` default: signatures 68, `== ALL` 60, `ALL` passed 62 | 190 | 7% |
| `.name` 50, `Family[...]` 25, K2 19, moved checks 9, mixed 6 | 109 | 4% |

So about 2,600 of the 2,708 are mechanical; real rewriting is ~110 lines, and 1,037 of
6,161 cells are touched. `enums.py` (1,577) and `spec.py` (597) are generated or copied.

What could be dropped if the compiler took upstream's spelling:

| upstream spelling the compiler would accept | sites that go away |
|---|---|
| a text literal compared with, or passed to, a label parameter (interned to an int at compile time; the generator's propagation finds every such position in 57/57 models) | 2,357 member spellings, all 56 `enums.py`, 380 Reference lines, 56 pickles, the forked-modelx dependency, the 56 `.name` and 25 `Family[...]` sites, the 9 check lines, the 2 pickled References |
| `kind=None` on a label parameter (`None` as one more interned value) | 68 signatures, 62 comparisons, 65 calls |
| a tuple of floats returned by a cell | 13 cells / 19 lines, one rewritten test |
| ranges inferred, or declared in the model beside the cell | 597 lines in 57 files outside the model |

## 6. Bottom line

The lean text is value-exact on the shipped books and regenerates cleanly; I found no
wrong number on valid upstream input. It is not a drop-in: it changes the calling
interface of 68 cells per upstream usage, silently accepts labels of the wrong family,
makes 13 cached vectors mutable against upstream's recent direction, breaks 8 of 57
shipped scripts and needs a modelx that is not released. About 96% of it is mechanical.

Smallest change I believe keeps compiled speed (speed itself unmeasured here):

* **With label interning in the compiler: 0 formula lines.** Upstream text stays; what
  remains is the range declarations, ~60 lines if reduced to one dict per model (597 as
  written), ideally stored in the model.
* **Without any compiler change: ~4,700 lines of `Projection` diff plus the generated
  enums** — the rename (2,029 lines replaced), defaults kept as `kind=Kind.ALL` (128
  lines instead of 190 and no call-site edits), text-valued members so that `.name`,
  `Family[...]`, the moved checks and the pickled References (≈95 lines) disappear, and
  no K2. That saves few lines over 7,240; it is the reliability findings D1–D7 it
  removes, not size. Size only falls if the compiler reads text labels.

Three conventions I would change:

1. **Members carry their label as value** (`StrEnum`, `DEATH = "DEATH"`), not a number.
   Upstream calls, scripts, tests, table keys and References keep working; a wrong
   family fails as upstream; no `.name`, no `Family[...]`, attributes stay text.
2. **Keep the default argument** (`kind=None`, or `kind=Kind.ALL`): `claims(t)` stays
   valid and the docstrings stay true. If a total member is kept, do not call it `ALL`
   where it omits a kind.
3. **Leave upstream's tuples and text References alone** (drop K2 and the two pickled
   References): keep cached values immutable, keep upstream's immutability test, keep
   every Reference readable in the model text.

Also worth fixing whatever else is decided: one family name per concept across models;
range declarations inside the model and checked against it; `run.py` and the docstrings
brought in line with the text they describe.
