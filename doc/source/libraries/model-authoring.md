# Expressions for regional projection models

Keep each CSV read in its Data Cell and return a pandas DataFrame or Series.
Use ordinary Python expressions for financial calculations. The same formulas
then run in live modelx, an exported Python model and a compiled model.

Use pandas indexing for table reads. A scalar lookup such as
`frame.loc[key, "column"]` names the key and field directly. Use `.iloc` for
positions and keep a complete tuple key for a MultiIndex lookup. A missing
key should raise unless the financial rule defines a default. Use `float()`
or `int()` when a formula requires that result type.

The compiler can use native reads for supported pandas layouts, key types
and expressions. Other operations, including report preparation, can keep
their pandas behavior. Write reductions with Python built-ins such as
`sum`, `any` and `max` and keep the iteration domain and filters explicit.

Treat category inputs as strings and convert them in the model with
`Category[label]`. Keep accepted aliases explicit, and let unknown labels fail
at the conversion Cell. Use named enum members in calculations that receive
already-converted categories.

## Give the compiler a representative sample

Use the same types, table layouts, key types and formula branches that the
production book uses. modelx Cells cache their results by default. Mark a
Cell as uncached in modelx if its formula needs to run on every call.
The compiler chooses the storage representation for a cached Cell.

Cached native signed-integer coordinates admit the range covered by
the sample, including observed negative indices. For a longer horizon, sample
it or declare the necessary upper extent using `cells_param_size` in the
Space's translation spec. For example, `{'cells_param_size': {'t': 361}}`
covers nonnegative `t` through 360. Include any needed negative indices in the
sample. Calls outside an admitted numeric cache range can raise `IndexError`.

For example, the MYGA model reads its policy data in this Cell:

```python
def model_point_table():
    return pd.read_csv(input_dir() / model_point_file, index_col="point_id")
```

For parallel calculations with shared tables, export with
`model.export(destination, locked_spaces=['Data'])` when Data owns the
shared Cells. Use their actual Space name when it differs.

## Check the build report

In the compiled package, open `_mx_admission.json` and find the consumer Cell.
`table_reads_untyped` lists reads left in pandas and `native_reductions`
counts admitted typed loops. `return_type` shows the generated representation.
`cache` shows
the storage choice. `dense_logical_domain` and `associative_logical_domain`
show the accepted integer ranges, with exclusive upper bounds. The optional
`dense_window` spec setting selects the physical dense region within an
admitted domain and leaves the Cell's authored cacheability unchanged.

Check `reasons` for Cells missed by the sample and reads that require the
source Space to be locked. Verify full policy outputs and check the consumer's
build report when changing a performance-critical formula.

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
