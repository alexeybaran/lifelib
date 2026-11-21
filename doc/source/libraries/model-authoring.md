# Expressions for regional projection models

Use pandas for input tables and ordinary Python expressions for financial
calculations. Keep each CSV read in a cached Cell in the shared Data Space. A
Projection Cell can then read the same table with the same formula in live
modelx, an exported Python model, and a compiled model.

| Expression | Domain and result | Native admission |
| --- | --- | --- |
| `pd.read_csv(path, index_col=...)` | Read a DataFrame keyed by the policy or assumption fields used by the model. Use a MultiIndex for compound keys. | Keep key and column types consistent in the sample. The compiler can prepare supported pandas layouts for recognized reads. |
| `frame.loc[key, "column"]`, `frame.at[key, "column"]`, `series.loc[key]` | Select a value by its complete label. Convert it with `float(...)` or `int(...)` when the financial formula calls for that type. | On a supported frame or series, a unique index and compatible sampled key types can admit a native read. Named DataFrame reads need a column known at build time. |
| `frame.loc[key]["field"]` or `frame.loc[prefix]` followed by a keyed read | Read a row field or select a group by its initial index levels. Keep tuple keys intact. | Supported field or prefix reads can use prepared data. A returned DataFrame or Series remains a pandas object. |
| `key in frame.index`, `frame.index.min()`, `frame.index.max()`, `frame.index.asof(key)` | Check a key or search an ordered index. Use an explicit missing-key value only where the model defines one. | The compiler can lower recognized membership, extrema and searches on supported index layouts. |
| `range`, `sum`, `all`, `any`, `min`, `max`, `zip` | Express policy calculations with ordinary iteration, filters and a meaningful initial value such as `0.0`. | Suitable ranges and yielded values can enable typed reductions. Check the generated admission report for the actual route. |

Treat category inputs as strings and convert them in the model with
`Category[label]`. Keep accepted aliases explicit, and let unknown labels fail
at the conversion Cell. Use named enum members in calculations that receive
already-converted categories.

Use `float(frame.loc[key, "rate"])` for a read that must produce a float. When
the scalar type matters, keep the original pandas selection result.

## Give the compiler a representative sample

Use the same types, table layouts, key types and formula branches that the
production book uses. modelx Cells cache their results by default. Mark a
Cell as uncached in modelx if its formula needs to run on every call.
The compiler chooses the storage representation for a cached Cell.

Cached native signed-integer coordinates admit the range covered by
the sample, including observed negative indices. For a longer horizon, sample
it or declare the necessary upper extent using `cells_param_size` in the
Space's translation spec. For example, `{'cells_param_size': {'t': 361}}`
can cover nonnegative `t` through 360. The integrated compiler also accepts
an explicit `(lower, stop)` pair, such as `{'cells_param_size': {'t': (-12, 361)}}`.
Include representative boundary values in the sample. A call outside the
admitted range raises `IndexError`. A value that
cannot enter a signed 64-bit native slot exactly raises an error naming the
Cell or Reference. Widen the sample or spec when the model needs a wider type.

The MYGA model reads policy inputs with this Data Cell:

```python
def model_point_table():
    return pd.read_csv(input_dir() / model_point_file, index_col="point_id")
```

Use the actual Space name in `locked_spaces` when shared state requires a
lock. For example, `model.export(destination, locked_spaces=["Data"])` locks
the source when the model's Data Space is the shared state that needs it.

## Check the build report

In the compiled package, find the consumer Cell in `_mx_table_reads.json`.
The report gives the recognized read form or the reason the expression stays
on pandas. Then consult `_mx_admission.json` for the generated return type,
cache representation and admitted native reductions. `dense_logical_domain`
and `associative_logical_domain` show the accepted integer ranges with
exclusive upper bounds. The optional `dense_window` setting selects the
physical dense region within an admitted domain.

The `reasons` field identifies Cells missed by the sample. A recognized read
can still fall back to pandas for a particular key or layout. Compare full
policy outputs and inspect the consumer's admissions when changing a
performance-critical formula.

## Run another scenario

In live modelx, changing a Reference triggers dependency invalidation. For an
exported or compiled model, create a fresh model instance or process and install
changed inputs before requesting its first calculation. For example, with a
compatible MYGA input CSV containing policy 1:

```python
from pathlib import Path

from MYGA_US_S_nomx_cy import mx_model

base_cashflow = mx_model.Projection[1].net_cf(1)
scenario = type(mx_model)()
scenario.Data.model_point_file = str(Path("myga_stress_points.csv").resolve())
scenario_cashflow = scenario.Projection[1].net_cf(1)
```

Use the same sequence with the exported Python package. Install every changed
input on `scenario` before calling a reader, a projection Cell or `collect`.
