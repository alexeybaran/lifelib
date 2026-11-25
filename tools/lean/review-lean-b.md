# Review of the lean conversion (branch `r4/l1-lean`, b6aad67, against upstream 20d4dae)

Independent review. Stack: Python 3.13, modelx `r4/modelx-integration` (df3ced9), pandas 3.1,
modelx-cython 0.1.0 from PyPI for one compile experiment. Every number below was measured
here; scripts are not committed (they read two checkouts and a scratch copy).

The generator reproduces the branch byte for byte (`lean.py generate --upstream 20d4dae`
over a fresh worktree of b6aad67: `git status` empty).

## 1. Kinds of change (counts over the 57 models)

Counts are from the lean vs upstream text, by AST/regex, and agree with the generator's
categories. I checked them against `git diff` on KLV_DE_S, IP_UK_S, FIA_US_S, Annuity_JP_S,
Child_KR_S and Rente_FR_S (numstat and my counts agree to ±1 line per model).

| kind (generator rule) | count | models | before → after (one example) |
|---|---|---|---|
| K1 label → member | 2,485 spellings; 2,049 changed lines are nothing but this | 56 | `claims(t, "DEATH")` → `claims(t, Kind.DEATH)` (KLV_DE_S `net_cf`) |
| K1 `None`/label default dropped | 68 `def`s | 54 | `def claims(t, kind=None):` → `def claims(t, kind):` |
| K1 `is None` → `== F.ALL` | 60 | 54 | `if kind is None:` → `if kind == Kind.ALL:` |
| K1 omitted argument passed | 62 call lines | 50 | `claims(t)` → `claims(t, Kind.ALL)` (57 `ALL` members exist only for this) |
| K1 value use `.name` | 56 uses on 50 lines | 20 | `.loc[(table, sex(), x)]` → `.loc[(table.name, sex(), x)]` (Annuity_JP_S) |
| K1 by-text lookup `Family[...]` | 25 | 12 | `return v` → `return Sex[v]` (RLV_DE_S `sex`) |
| attribute cells returning members | 17 cells (subset of the above) | 12 | `sex()`, `smoker()`, `grade_*()`, `credit_method()`, `glwb_basis()` |
| References: family classes | 189 (`Kind = ("Pickle", 5)`) | 56 | 378 inserted lines |
| References: member values | 2 | 2 | `tariff_table_sex = "F"` → `("Pickle", 5)` (Rente_FR_S), `ref_sex` (Child_KR_S) |
| K2 tuple → list | 17 lines, 13 cells | 5 | `return tuple(f(z) for z in zs)` → `return [f(z) for z in zs]` (BU_DE_S, IP_UK_S) |
| check-then-convert overrides | +11/-2 | 2 | FIA_US_S `credit_method`, Dep_FR_S `carence_factor` |
| `enums.py` | 1,577 lines, 189 classes, 50 names, 842 members | 56 | new file |
| storage | `enums = ("IOSpec", 1)` +5 lines; `_data/iospecs.py`; `data.pickle` | 56 | new |
| K3 `spec.py` | 597 lines: 57 dict lines + 540 comment lines | 57 | new file |
| tests (not in the 7,240) | +2,919/-2,465 in 69 files, incl. a 212-line text→member shim in `sec_support.py` | 6 libs | `p.claims(t, "DEATH")` → `p.claims(t, Kind.DEATH)` |

No per-step pandas hoist is applied: `hoists` is off in every override.

## 2. Convenience (would an actuary write it this way? what got harder?)

* **K1 members at call sites** — readable (`Kind.DEATH` reads like `"DEATH"`), and a typo
  fails at the name lookup instead of falling through to `raise ValueError`. An actuary
  would write it unprompted only if the enum module were importable in the formula
  namespace by convention; today the names come from `("Pickle", n)` References that the
  text does not show. Harder: up to 793 docstring mentions of ``"LABEL"`` and 45 models' docstrings
  ("the total when kind is omitted") now describe calls that fail (§3, R2/R3).
* **Dropped `kind=None`** — a regression for readers and callers: `claims(t)` was the
  natural spelling of "total"; it is now `claims(t, Kind.ALL)` with a member upstream never
  had. Keep the default (a compiler can treat `None` as one more slot).
* **`.name` at the data boundary** — fine as a rule, but round trips appear: Child_KR_S
  `basis_param(BasisParam["surgery_rate_" + cause.name])` then `name.name` inside. No
  actuary writes that; it exists only so a table key can be an integer argument.
* **Attribute cells returning members** — the worst for readers: `p.sex()` shows
  `<Sex.M: 0>`, `p.sex() == "M"` is `False`, and `f"{p.sex()}"` is `"0"` (IntEnum `str` is
  the integer since 3.11). Six shipped `run.py` scripts now print `035 0` for `M35 N`.
* **Member References** — `tariff_table_sex = "F"` was a visible assumption in the text;
  it is now an opaque pickle id. Leave labels that are inputs as text.
* **K2 lists** — upstream main made IP_UK_S `sick_cohorts`/`claim_rate_vectors` tuples so a
  caller cannot corrupt the cache; the lean text reverts that and deletes the test that
  guarded it (R5). Tuples read the same and should stay.
* **`spec.py`** — the 540 comment lines cite line numbers of a text (04d69db) that is not on
  the branch and not fetchable here; they are already wrong for the lean text
  (KLV_DE_S "lines 2202-2486" points at a docstring).
* Family naming is not uniform across models: `Kind` (44), `ClaimKind` (5), `Claim` (8)
  for the same idea; `Kind.DEATH` is 0 in one model and 1 in another.

## 3. Reliability: inputs where lean and upstream differ (live modelx)

Baseline: 43 of 57 models re-run here cell by cell (no-argument cells, all points): 17,498
cells, 0 value or error differences, 172 type-only differences (members for strings in 6
models; lists for tuples in BU_DE_S, IP_UK_S, VA_KR_S). The other 14 were stopped for time.

| # | reproduction (`p = m.Projection[1]`) | upstream | lean |
|---|---|---|---|
| R1 wrong family | KLV_DE_S `t = p.proj_len()-1`; `p.claims(t, PolsTiming.AFT_MORT)` (upstream `"AFT_MORT"`) | `ValueError: invalid kind` | `28750.90` = MATURITY claims, silently |
| R1b | `p.claims(t, 1)`, `p.claims(t, True)`; `p.pols_if_at(5, Kind.MATURITY)` | `ValueError` | value (IntEnum compares as int; every family starts at 0) |
| R2 upstream spelling | KLV_DE_S `p.claims(0, "DEATH")`; Child_KR_S `p.sum_assured("cancer")` | `3.68`; `10000000.0` | `ValueError: invalid kind`; `AttributeError: 'str' object has no attribute 'name'` |
| R2b unknown text label | Child_KR_S `p.sum_assured("bogus")` | `KeyError: 'sa_bogus'` | `AttributeError` (another error type) |
| R3 omitted default | KLV_DE_S `p.claims(0)` (68 cells) | `3.68` | `TypeError: missing a required argument: 'kind'` |
| R4 attribute type | RLV_DE_S `p.sex() == "M"`; `str(p.sex())` | `True`; `'M'` | `False`; `'0'` |
| R5 cache mutation | IP_UK_S `p.sick_cohorts(2)[1] = 999.0`, then `p.pols_sick(3)` | `TypeError` (tuple); `0.000305` | accepted; `954.94` |
| R6 Reference as text | Rente_FR_S `m.Projection.tariff_table_sex = "M"`; `p.taux_rente_tariff()` | `0.0373` | `ValueError: invalid table_sex` |
| R7 blank label | CI_UK_S `sex` empty in point 1 | `KeyError: 'NS'` (result_cf) | `KeyError: nan` |
| R7b | FIA_US_S `credit_method` empty | `credit_method()` returns NaN, error later | `ValueError` in `credit_method` |
| R8 shipped scripts | `python products/<p>/run.py` on all 57 | 57 run | 8 crash (Annuity_JP, CI_UK, Cancer_KR, Child_KR, FIA_US, Obseques_FR, VA_US, WP_UK); 6 print digits for labels (Endowment_JP, LTC_JP, LTC_KR, RLV_DE, Rente_FR, Sofort_DE) |
| R9 longer projection | live modelx does not read `spec.py` | — | no difference live; compiled, see below |

R7/R7b are the documented "same type, another message / earlier cell" cases; NaN behaves
like the `ZZ` runs in RESULTS.md. R1, R2b, R4–R6, R8 are not in RESULTS.md.
`check.py` hides R4 by design (`norm` maps a member to its name before comparing).

Compiled (KLV_DE_S, modelx-cython 0.1.0, the lean `spec.py`): the spec is model level
(`{'cells_param_size': ...}`); 0.1.0 reads sizes per space (`spaces.Projection`, the shape
upstream's own `spec_sec.py` uses), so `t` was sized from the sample (360, not 481) and
the `kind` axis of `claims` got 3 slots: compiled `claims(t, Kind.ALL)` raises
`IndexError: array index out of range`. Whatever compiler the owner uses, the member
count of a family is a range the convention should declare (or the compiler derive).

Speed, not verified: with 0.1.0 both texts of KLV_DE_S compile (upstream's `kind` becomes
`str` with a `dict` cache, lean's `long long` with an array), but neither compiled
`result_cf()` runs: `res_guar_pp(k - 1)` reads `k = -1`, which the spec comment notes and
the 0.1.0 spec cannot express (`IndexError`). On a path that runs (`pols_if_at`, `mort_rate_mth`,
14 points) compiled and pure Python take the same 0.55–0.71 s for both texts, because the
per-step pandas reads are still there (no hoist is applied). The owner's compiler build must
differ from 0.1.0; the speed claim rests on runs I could not reproduce.

## 4. Generic: a one-page guide, or the generator?

The conventions can be written on one page and need no generator:
1. one `enums.py` per model, `IntEnum` per family; 2. a typed parameter receives a member;
3. a table key or column built from it uses `.name`; 4. text from data is converted once,
after upstream's validation, with `Family[text]`; 5. sequences are lists; 6. per-space
ranges. Storage is three modelx calls (`mod = m.new_module("enums", "enums.py", path)`,
`m.Projection.Kind = mod.Kind`, `m.write(...)`); I built and re-read a toy model that way.
What a guide cannot carry today: family and member names come from `reference/*.json`,
derived from a full conversion (04d69db) absent from this branch, so the generator cannot
convert a model outside the 57 and a rebase that adds a label needs a hand edit there.
After the change lands as upstream text, the generator (2,262 py lines, 634 toml, 444 KB of
reference maps) can be dropped; keep a ~50-line lint test instead (no string compared with a
typed parameter, no family mixing, enums stored). It also depends on the modelx fork (S4)
to read `("ModuleAttr", 1, "Family")`.

## 5. Size: mechanical vs real

Of the 7,240 counted lines (Projection/Data 5,059, enums 1,577, spec 597):
mechanical renaming 4,098 (2,049 pairs) + family References 378 + `enums.py` 1,577 = 6,053;
default removal and `ALL` passing 380 (190 pairs); `.name`/lookups ~150; K2 34;
overrides 13; `spec.py` 597 (57 of them data). Real rewriting is under 600 lines.

If the compiler handled upstream's spelling, these could be dropped:
* **string label constants at typed positions** (2,485 sites): the compiler interns a
  parameter's closed set of string constants to ints. Drops K1 renames, `enums.py`,
  References, `.name` (56), lookups (25), overrides, storage files and all test edits.
* **`kind=None`** (68 defs, 60 tests, 62 calls): `None` as an extra slot.
* **tuples** (13 cells, 17 lines): a homogeneous tuple typed like a list.
Evidence: 0.1.0 already compiles upstream's `claims(self, long long t, str kind=*)`,
caching it in a `dict` where the lean text gets a `double[360][3]` array.

## 6. Bottom line

Smallest change that I believe keeps compiled speed with today's compiler: the K1 member
spellings on typed parameters and their `enums.py` (≈6,000 lines, nearly all mechanical),
keeping `kind=None` defaults, attribute cells and References as text, and tuples; i.e.
drop ≈450 lines of the current change. With a compiler that interns string labels,
upstream text plus 57 one-line range dicts (~57 lines).

Three conventions I would change:
1. **No cross-family equality**: give every family in a model disjoint values (e.g.
   `Kind` 100+, `PolsTiming` 200+), or a plain `Enum` if the compiler allows it, so a wrong
   family or bare int reaches upstream's `raise ValueError` instead of a value (R1).
2. **Members only inside the model**: attribute cells, References and public defaults keep
   upstream's text and `None`; convert at the typed call, not in what users read (R3, R4, R6, R8).
3. **Ranges per space, derived**: `spec.py` in the shape the compiler reads
   (`spaces.Projection`), family axes sized from `len(Family)`, no line-number comments.
