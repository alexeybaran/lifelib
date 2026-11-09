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

For a Table use `lookup_float(table, complete_key, column[, default])`.
For a Record use `lookup_float(record, field[, default])`.
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
override = tables.lookup_object(policy_record(), 'annuity_rate_override', None)
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
uses an existing Table to own unique ordered labels; it leaves the public Index
and its metadata unchanged. Duplicate-label preparation is rejected explicitly
and remains a separate source-operation compatibility/native-coverage obligation.

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
