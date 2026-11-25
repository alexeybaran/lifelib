# Writing a model in the lean style, by hand

For an actuary writing a new `*_S` model (or editing one) so that a compiler can type its
label arguments, without the generator. Everything not named here is written as usual.
Python 3.11 or later (for `enum.StrEnum`).

## 1. Declare a family

A *family* is the closed set of text labels one cell parameter takes: the `kind` of
`claims(t, kind=None)`, the `timing` of `pols_if_at(t, timing)`. Put every family of the
model in one file beside the model's spaces, `<Model>/enums.py`:

```python
from enum import StrEnum


class Kind(StrEnum):
    DEATH = "DEATH"
    MATURITY = "MATURITY"
    LAPSE = "LAPSE"


class PolsTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    AFT_MORT = "AFT_MORT"
    AFT_LAPSE = "AFT_LAPSE"
```

* One plain `class Name(StrEnum)` per family; each member is `NAME = "label"`, where
  `"label"` is exactly the text the model would otherwise use, and `NAME` is that text
  when it is a valid identifier. Nothing else in the file: no methods, no metaclasses, no
  helper classes, no integers.
* List every label the parameter can take, including labels that arrive only from data
  (a `"mix"` sex read from the model point file). Do not add a member for "no label":
  a `None` default stays `None` (section 3).
* Use one family per parameter meaning. Two parameters share a family only if they take
  the same set of labels.

Store the file with the model, once, from a modelx session (modelx with module storage,
branch `r4/modelx-integration`):

```python
m = mx.read_model("MyModel_S")
enums = m.new_module("enums", "enums.py", "path/to/enums.py")
for space in (m.Projection,):                 # each space that spells a family
    space.Kind = enums.Kind
    space.PolsTiming = enums.PolsTiming
m.write("MyModel_S")
```

This writes `enums.py`, `_data/iospecs.py` and `_data/data.pickle` into the model folder
and the References `enums = ("IOSpec", 1)` and `Kind = ("Pickle", n)` into the text.
Afterwards, edit `enums.py` in the folder as text; re-run the four lines only when a space
starts or stops spelling a family.

## 2. Spell labels as members where the model itself writes them

Inside the formulas, a label that is passed to, or compared with, a family parameter is
written as the member:

```python
def claims(t, kind=None):
    if kind is None:
        return sum(claims(t, k) for k in (Kind.DEATH, Kind.MATURITY, Kind.LAPSE))
    if kind == Kind.DEATH:
        return pols_death(t) * sum_assured()
    ...
    raise ValueError("invalid kind")

def net_cf(t):
    return premiums(t) - claims(t, Kind.DEATH) - claims(t, Kind.MATURITY) - ...
```

That is the whole edit for a typical cell. Keep the final `raise ValueError(...)`: a label
of another family (`PolsTiming.AFT_MORT`) or an int is not equal to any `Kind` member and
still reaches it.

## 3. What stays exactly as you would write it without families

A member *is* its label text (`Kind.DEATH == "DEATH"`, same hash, prints `DEATH`), so:

* **defaults**: `kind=None`, `if kind is None:`, calls that omit `kind`; a text default
  `weighting="count"` stays text;
* **table keys and columns**: `table.loc[(sex, x), "q"]`, `df[kind]`, f-strings and
  messages use the parameter as it is (no `.name`, no `.value`);
* **References**: `tariff_table_sex = "F"` stays text;
* **attribute cells** (`sex()`, `smoker()`) return the text from the model point, unless
  their result is passed on as a family argument (section 4);
* **callers**: scripts, tests and notebooks may pass `"DEATH"` or `Kind.DEATH`; both hit
  the same cache entry.

## 4. A sequence of numbers is a tuple

A cell that returns several numbers at once (a cohort vector, a list of ids, anchor
pairs) returns a **tuple**, not a list:

```python
def sick_cohorts(t):
    ...
    return tuple(prev[z - 1] * surv[z - 1] for z in range(1, n))

def subaccount_ids():
    return tuple(data.subaccount_table().index)

def dis_cohorts(t):
    pols = [0.0] * n                        # build a local list as usual ...
    ...
    return tuple(pols), tuple(val)          # ... and return it as a tuple
```

Two reasons. The compiler accelerates tuple-returning cells only; a cell that returns a
list stays an ordinary Python object (correct, but about nine times slower). And modelx
caches the returned object itself: a caller that changes a returned list changes the
cached value every later formula reads, silently; a tuple cannot be changed. So never
write into a returned sequence; build a new one. (Lists of text, such as messages, may
stay lists.) If a test or a caller needs a list, it converts the value itself:
`list(dis_cohorts(t)[0])`.

## 5. Where text from data becomes a member

Only where a label read from data (or built from text) is **passed on** as a family
argument, convert it once, by name, in the cell that reads it:

```python
def sex():
    v = model_point()["sex"]
    if v not in ("M", "F"):                 # the check you would write anyway, first
        raise ValueError("invalid sex")
    return Sex[v]

def comm_rate(y):
    return charge_rate(ChargeLine["comm_yr%d" % y])
```

`Family[text]` raises `KeyError` for an unknown label. If the model has its own check with
its own error for that label, put the check before the conversion (as above), so the
caller sees that error. A label read from data that is only used as a table key or
compared with text needs no conversion.

## 6. Can a lint check it?

Yes, the mechanical part, in about a hundred lines of `ast` over the model folder, with
no modelx:

* `enums.py` holds only `class X(StrEnum)` bodies of `NAME = "text"` assignments, and
  every member's text is unique within its family;
* in each cell, a parameter compared with a member of one family is never compared with,
  or passed, a member of another family or a bare string literal (the forgotten
  `"DEATH"`);
* at every call to that cell, the argument at that position is a member of the same
  family, a parameter of the caller typed the same way, `None`, or a `Family[...]`
  lookup, never a string literal;
* every family a space spells is a Reference of that space, and every family Reference
  names a class of `enums.py`;
* no cell returns a list display, a list comprehension, `list(...)` or a local bound to
  one (a sequence of numbers is returned as a tuple).

What a lint cannot see is a label that arrives from data and is passed on without a
`Family[...]` conversion: the value is still right (a member is its text), only the
compiler loses the type. A test that runs each attribute cell feeding a family argument
on the shipped book and asserts it returns a member covers that.

## 7. Tests changed against upstream

Every upstream test runs unchanged, except these generated edits:

* **The two hot cells made tuples.** A cell's value is immutable, and a tuple is the
  vector form the compiler accelerates. So each test line that needed a list now takes
  a tuple, or builds a new value. What it asserts is unchanged.
  * `frlib/tests/test_assurance_emprunteur_fr.py`, in
    `test_the_cohort_vector_is_rebuilt_not_mutated`: `snapshot = list(a)` becomes
    `snapshot = tuple(a)` (`itt_cohorts`).
  * `frlib/tests/test_dependance_fr.py`: `p.dep_cohorts(30)[0][0] = 999.0` becomes
    `held = list(p.dep_cohorts(30)[0]); held[0] = 999.0`. The test still asserts that
    the cached `pols_part(30)` is unchanged.
* **The model folder holds more files.** The six `test_model_conventions*` modules allow
  `enums.py` and `_data/` there. Seven product tests list the folder and now expect those
  files:
  * Pflegerentenversicherung (DE);
  * Assurance Emprunteur, Assurance Vie Euro, Dépendance, PER and Rente Viagère (FR);
  * Variable Annuity (KR).
* **SEC comparisons.** Three uslib SEC tests compare the SEC model's References with the
  S model's. They leave the family classes and `enums` out of that comparison:
  `test_variable_annuity_us_sec`, `test_indexed_ul_us_sec` and
  `test_guaranteed_ul_us_sec`.

Four other list-returning cells stay lists, because a test compares them with a list or
they hold text: CI_KR_S `ci_cohort_ids`, Medical_KR_S `sev_points`, VA_US_S `sub_ids` and
DIA_US_S `qlac_flags`.
