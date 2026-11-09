# Explicit typed table operations

The same function names and arguments work in live modelx, `model.export()`
Python, and Cython-compiled models. Preparation is explicit and uses the existing
immutable `Table` and `Record` types; no second table framework is introduced.

```python
# Data preparation Cell, dependent on the public pandas Cell:
def mortality_table():
    return inputs.table(mortality(), columns=('rate',), indexing='loc')

# Projection expression:
return tables.lookup_float(data.mortality_table(), (sex(), age()), 'rate')

# Keep the public model_point Series. Prepare a separate internal Record:
def policy_record():
    return inputs.record(model_point(), preserve_scalar_types=True)

return tables.lookup_int(policy_record(), 'age_at_entry')
```

`inputs` is `lifelib.pandas_inputs`; `tables` is `lifelib.typed_inputs`.
Ordinary function References can be used instead of module References.

| Function | Python result | Cython declaration | Conversion |
| --- | --- | --- | --- |
| `lookup_int` | `int` | `long long` | `int(value)`, checked signed 64-bit range |
| `lookup_float` | `float` | `double` | `float(value)` |
| `lookup_bool` | `bool` | `bint` | `bool(value)` |
| `lookup_str` | `str` | `str` | `str(value)` |
| `lookup_object` | original scalar | `object` | none |

For a Table use `lookup_float(table, complete_key, column, default=...)`.
For a Record use `lookup_float(record, field, default=...)`.
Omit `default` when a missing key should raise. Use the keyword consistently.
A Record has fields rather than columns: supplying its third positional
argument or `column=` raises TypeError. Table column selection keeps its
ordinary declared `column` slot, including existing positional calls. This
retires an unused unqualified Record-default prototype spelling; all1,183
regional policy reads already use two arguments and need no model edit.
The optional default is converted by the same rule as a found value; it is used
only for a missing key, not to mask conversion or column errors. Argument
expressions evaluate once, from left to right, before lookup. A complete tuple
key remains one key, so an earlier group lookup cannot skip a later key expression.

`lookup_int` rejects results outside `[-2**63, 2**63)` in all three modes. It does
not silently wrap or approximate large integers. Other conversion errors are
preserved, including `float(None)`, invalid numeric strings, and ambiguous
`bool(pd.NA)`. `lookup_object` preserves `None`, `pd.NA` and `pd.NaT` identity.
It is an explicit object-valued operation, not evidence of primitive arithmetic.

For an optional actuarial override, use the scalar predicate explicitly:

```python
override = tables.lookup_object(policy_record(), 'annuity_rate_override', default=None)
return default_rate() if tables.is_missing(pd.isna, override) else float(override)
```

`is_missing(predicate, value)` returns a boolean. Passing the current predicate
first preserves its resolution before the value is evaluated, and keeps ordinary
predicate Reference replacements working. The canonical pandas scalar predicate
uses native checks for the inventoried builtin/NumPy numeric and boolean values,
strings, `None`, `NA` and `NaT`. Noncanonical predicates and unsupported values use
the original predicate and remain compatibility paths, not native coverage.

The provider's `.pxd` declares these result types directly. The compiler's
existing registered-symbol linker connects a named function Reference or one
registered module member to that declaration. There is no pandas/formula
interpreter and no AST parser or `float(lookup(...))` expression recognizer in
this mechanism. Cython checks and compiles the declared call normally.

The shared registered-call ABI also preserves authored keyword order, omitted
arguments and explicit `None`. Its provider-owned omission token is internal;
actuarial expressions do not name it. A replacement receives the same positional
and keyword arguments, before interpretation of Record defaults. The compiler
reads declared signatures and registered metadata, never callback bodies.
The six helpers require the shared keyword/scalar ABI introduced by compiler
`931faba`; that development bundle retains qualified architecture `299d8c1` as
its base and still requires regional qualification.
Provider replacement forwarding uses the single compiler-owned
`_call_layout.pxd` header introduced at `3f99c12`; float-state C names reexport
the shared `_float_sum_state.pxd`. These are header-only dependencies, with no
runtime import of an unbuilt native table-provider binary. A Cython source build
must be able to discover the compiler package's headers.

Table reads compose with the generator lane's existing functions:

```python
return streams.sum_float(
    streams.periods(proj_len()),
    lambda t: tables.lookup_float(data.mortality_table(), (sex(), age_at(t)), 'rate',
                                  default=0.0) * exposure(t),
    where=lambda t: exposure(t) > 0.0,
)
```

Here `streams` is `lifelib.expression_streams`. The filter executes before the
read. Arguments and defaults are eager when that callback executes, not when
the stream is first authored. `sum_float` is the float-converting consumer;
ordinary mixed-type sums retain their separate contract. Physical ABI metadata
does not itself prove native callback or complete model coverage.

Native full-key lookup admits exact string, bool, signed-int64 and finite float
components, and complete tuples of up to four components. Integral floats and
integers follow exact Python key equality without converting large integers to
double. NumPy integer, boolean and float16/32/64 query scalars use the same native
key path where their value fits the declared domain, retaining original error
argument scalar types. Unsupported keys retain compatibility behavior and remain a coverage
gap until separately implemented and evidenced. Native resources are owned by
the immutable input and rebuilt after unpickling. They hold no policy cache.

The current callable is passed to the provider. Replacing it with a callable
that obeys the same typed result contract invokes that callable with the original
arguments. This compatibility path uses Python and is not native coverage.
Registered typed functions have a fixed result contract; arbitrary replacements
that change that result type cannot satisfy the declared native ABI.

Public DataFrames, Series and Indices keep their public contracts. Preparation
copies selected inputs rather than changing the public pandas objects. Final
public pandas construction remains an explicit materialization boundary; its
labels, column order, index classes/names, dtypes and missing entries must be
validated, and its cost counted separately and in the full lifecycle.

`record(row, preserve_scalar_types=True)` copies the actual `row[field]` scalar
types, including NumPy integers/floats/booleans. The default normalizes NumPy
scalars for numeric preparation. This choice is explicit because `Series.items()`
and `Series[field]` can yield different scalar classes. `index(public_index)`
owns unique ordered labels in an existing Table and duplicate labels in an
existing Record containing the owned key tuple. It leaves the public Index and
its metadata unchanged. `keys` preserves label order and multiplicity in both
representations. Integer, finite-float and string spans traverse these owned
labels through the same native producer ABI, including cold/hot resources and
pickle rebuilds. A duplicate-label traversal input does not turn ambiguous labels
into unique table lookups. Tuple/MultiIndex label consumers need their own native
proof; ordinary object iteration is not that proof.

Index snapshot construction currently remains an explicit Python preparation
boundary, as in the existing adjusted input approach. Direct-Cython tests prove
native span construction/traversal without Python `keys`, Table or Record method
calls. They do not qualify complete native input preparation or a model whose
Index/selection/report source has not yet been migrated and validated.

Live modelx tracks whole-value replacement through normal dependencies. Edits
inside a pandas object are not tracked. Exported and compiled models do not
automatically invalidate caches; callers must explicitly clean up/rebuild as
before. A fresh model instance is one supported full cleanup. Preparation must
depend on the public source Cell so Cell overrides are respected.

The native level is compared to the existing adjusted MYGA/VA providers: compiled
provider calls and native numeric storage, with CPython C APIs for ownership,
strings, conversion/errors and object-valued contracts where required. Zero
Python helper invocations is tested separately from primitive-only execution.
Neither successful compilation nor a zero-call profile alone qualifies an entire
regional model. Full operation coverage, financial validation, generated-code
evidence and matched performance remain separate gates.

## Row and column expressions

`lifelib.table_operations` provides two more directly registered selectors:

```python
prepared = inputs.table(result_cf(), rows=True)
selected = operations.row(prepared, t)
claims = sum(tables.lookup_float(selected, name)
             for name in keys(selected) if name.startswith('claims_'))
rates = operations.column(prepared, 'rate')
```

`row(table, key)` selects one unique row into the existing Record from an
ungrouped Table prepared with `rows=True`. Row coercion follows the selected
columns, so pruning columns can change a row dtype. Preparation
owns the actual pandas row scalar coercion separately from column values:
an int64 column beside a float64 column stays integral for column lookup,
while the selected pandas-style numeric row contains float64 scalars. Nullable
missing singletons, field order, row name and output dtype are retained.
`column(table, name)` returns ordered immutable values, with the same scalar
normalization as existing Table column lookup. It is not a Series, does not
align values by labels, and does not imply pandas skip-missing reductions.

`keys(table)` gives row keys. `keys(record)` gives ordinary field names. An
explicit owned Index snapshot has a private tag, so a real policy field named
`keys` is never mistaken for an Index's label tuple. Duplicate Index traversal
keeps its original order and multiplicity. Old Table/Record constructor and
unpickling forms remain valid; private native caches are discarded on pickle.

The two selectors use the existing `_native_inputs` provider and shared keyword
ABI. Exact owners and admitted lookup-key domains use native Cython selection,
with no Python helper, pandas indexing or Python Table/Record methods. Cold/warm
selection and output metadata were tested in live, exported and compiled modes.
This has the object-capable/CPython ownership level of the existing MYGA/VA
providers, not a claim that values or allocation are entirely unboxed. Replaced
callables, subclasses and unsupported key domains retain compatibility behavior;
those fallback executions do not establish native coverage.

`inputs.table(frame, report=True)` prepares exact public report metadata without
row snapshots; `rows=True` includes that metadata. Plain lookup preparation
omits both costs. `operations.to_pandas(table)` constructs the public DataFrame from preserved
metadata. `to_pandas(selected_row)` constructs its Series. The boundary restores
axis classes/names, column order, dtypes, missing entries, attrs and duplicate-label
flags and returns independent public objects. `index_name=` explicitly renames the
axis (`None` clears a single-level name; a MultiIndex requires a sequence of
names, following pandas rename); omission preserves its names. Untagged Records and Tables
without report metadata are rejected instead of guessed into report schemas.

Preparation with `rows=True` explicitly owns a second row-scalar matrix;
lookup-only preparation omits this cost. Preparation still uses Python and
pandas, as does final public materialization. Their costs/storage must be included
in lifecycle measurements. Native preparation, primitive column consumers,
grouping, arbitrary selection/alignment, and complete regional source migration
remain separate open gates. No full-model completion or performance claim follows
from selector tests.

## Grouped cash-flow reports

```python
monthly = inputs.table(result_cf(), report=True)
annual = operations.group_sum(
    monthly, [duration(t) + 1 for t in keys(monthly)],
    first='pols_if', last=('av_pp',))
return operations.to_pandas(annual, index_name='policy_year')
```

`group_sum(table, labels, *, first=(), last=())` puts first columns first, then last
columns, then summed columns in their source order. A single column name or a
sequence is accepted for first/last; duplicate state columns raise ValueError.
First/last select the first/last nonmissing value independently in each column.
Labels remain explicit actuarial expressions: duration+1, plan-year months//12
and positional twelve-row buckets are different operations. Canonical labels
are eager lists or tuples, not a promised arbitrary streaming input.

The current native domain is float64 columns and builtin signed-int64 or float
labels in lists/tuples. Missing float labels are dropped; all-missing states and
empty index/column dtypes are preserved. The provider runs a compensated C sum
for ordinary groups. Installed pandas' explicit segmented-ufunc capability also
selects NumPy's C reduceat for monotonic group ids without NaNs in the sum block,
matching its cancellation behavior. No pandas grouping or Python helper executes
inside either admitted kernel; CPython/NumPy C APIs own objects and buffers.

Other dtypes, Series label alignment, old metadata layouts and unsupported label
objects keep the pandas reference behavior through compatibility execution. Those
paths are not completed native coverage. Exact warning source locations differ
between Python reference and compiled calls; warning-filter/location behavior
remains an explicit semantic review obligation. Generic malformed-column/error
ordering in prepared source tables also remains open.

The kernel passed27 direct selection/group cases and one normal live/export/native
report/cache/pickle probe. All11 original annual grouping models passed127 original
policy cases with bit-exact financial values, axes/dtypes and output pickle
roundtrips, with no Python helper/pandas calls in the grouped kernel. Original
monthly inputs and actual authored group labels/state-column calls were observed;
annual outputs were never used as calculation templates. This is kernel proof,
not yet annual source migration or whole-model native/performance qualification.

## Native preparation of ordinary numeric reports

The existing `inputs.table(frame, report=True)` and `rows=True` constructors now
have a direct declared Cython operation. Canonical single-block float64 DataFrames
with string columns, basic integer Index/RangeIndex axes and empty attrs copy
through C buffers into the existing Table/Record owners. Read-only and strided
blocks, empty axes, original axis classes/names, row scalar classes, flags and
source-independent snapshots are preserved. No pandas methods, Python constructor
helper or Python Table/Record initializer executes on this admitted path.

Constructor selection does not change the public Python signature or defaults.
Replaced functions preserve original keyword order/omission through the shared
binder. Other blocks/axes/attrs, grouped or pruned-column preparation, and minimal
lookup-only construction retain reference preparation and remain explicitly outside
this native-constructor proof. The private physical-storage adapter is tested and
pinned with its pandas/NumPy versions; future layouts require qualification.

Native constructor and grouped reduction together pass127 original policy cases
across all11 annual grouping models with bit-exact output metadata and pickle
roundtrips and zero Python helper/pandas frames in preparation/grouping.116 focused
constructor/lookup cases and4 normal combined integration probes also pass. The
constructor tests caught and fixed one Python placement property and an integer-axis
boolean-query guard. Their negative histories are retained. This does not establish
annual source migration, full-model native coverage or performance acceptance.
