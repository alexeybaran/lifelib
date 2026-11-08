# Explicit numeric inputs from pandas

The experimental `lifelib.pandas_inputs` API prepares owned numeric lookup
resources while public model tables and reports remain pandas objects.

```python
from lifelib.pandas_inputs import numeric_table, lookup

# In an explicitly cached preparation Cell:
rates = numeric_table(mort_table())

# In a scalar actuarial expression:
q = lookup(rates, (sex(), age(t)), 'mort_rate')
```

`lookup` specifies `float(snapshot.loc[key, column])`, including its pandas
selection and error behavior. `numeric_table` copies at the preparation boundary;
a source edit affects a new snapshot. A model must explicitly connect preparation
invalidation to its source rather than assume mutable pandas objects stay stable.
This API does not silently change existing model input/cache contracts.

The Cython provider admits unique ordinary index/column axes and primitive
numeric columns up to 64 bits; it loads prepared float64 values directly.
Unsupported dtypes, duplicate labels, partial keys, unusual labels, unknown
columns and replaced helper callables retain the Python/pandas path. Numeric
conversion follows the explicit float-result contract. Fallback is compatibility,
not evidence of completed native coverage. `.at`, positional indexing, grouping,
mask alignment and output construction are separate operations.

The normal provider registration and numeric-return ABI support live modelx,
exported Python and generated Cython without model-specific compiler branches.
Both provider entries preserve current helper binding; numeric keys remain
objects at the ABI so boolean labels are not coerced to integers. Disposable
context state reconstructs after pickle. Public pandas report construction and
CSV I/O remain visible boundaries requiring their own validation and accounting.

This initial kernel is an experiment, not a claim of native execution of every
regional pandas operation. No core promotion is implied.
