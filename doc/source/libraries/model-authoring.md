# Expressions for regional projection models

Use `modelx_helpers.pdn` for owned inputs and ordinary Python expressions for
financial calculations. Keep each CSV read in its Data Cell. A Projection Cell
can then select the values it needs through the same formulas in live modelx,
an exported Python model, and a compiled model.

| Expression | Domain and result | Compiled execution |
| --- | --- | --- |
| `pdn.table(frame, columns=..., groups=...)` | A pandas DataFrame with unique leaf keys and unique string columns. Specify groups by index-level name. Group selection returns a Record or leaf Table. | DataFrame construction and selection use pandas. A provider may prepare a native view for supported dtypes and key domains. |
| `pdn.record(series)` and `pdn.index(labels)` | An owned row or ordered labels. Use `preserve_scalar_types=True` where the exact pandas or NumPy scalar type is observable. | Preparation uses Python. A provider can admit a specific scalar read or key operation. |
| `pdn.lookup_float(table, key, column)` and `pdn.lookup_int(...)` | A complete scalar or tuple key and a named column. These operations explicitly convert the selected value. Supply a default only when a missing key has a modeled value. | Supported owner, key, column and value domains may use a typed read. A call with a dynamic domain retains its ordinary object semantics. |
| `pdn.lookup_bool`, `pdn.lookup_str`, `pdn.lookup_object` | Use the result type called for by the formula. The object form preserves observable scalar types and missing values. | Declared scalar reads may be typed. Object results retain their Python behavior. |
| `record[field]`, `table.slice(key)`, `pdn.previous(table, key, column)` | Read an exact field, select a prepared row or group, or select the previous ordered key. Keep complete tuple keys distinct from scalar keys. | Native admission depends on the declared read, owner, key type and stable input binding. A sparse or mixed domain can use object operations. |
| `pdn.keys`, `pdn.first_key`, `pdn.last_key`, `pdn.contains` | Read key order or test membership. When the financial rule caps an integer input to the table boundary, show that rule in the formula. | Supported ordered numeric keys may use a native operation. The compiler retains the authored membership and boundary checks. |
| `range`, `sum`, `all`, `any`, `max`, `zip` | Use explicit periods and preserve input order, filter conditions, and a meaningful initial value such as `0.0`. | A reduction can run natively when the iteration and scalar operations are admitted. An object reduction follows Python semantics. |
| `pdn.column`, `pdn.group_sum`, `pdn.to_pandas` | Use `report=True` when preparing an input for pandas output. Use `rows=True` for pandas-style row selection. In grouped reports, specify state columns with `first=` or `last=` and sum the flow columns. | Supported numeric grouping may run natively. Materializing the public pandas result uses Python. |

Treat category inputs as strings and convert them in the model with
`Category[label]`. Keep accepted aliases explicit, and let unknown labels fail
at the conversion Cell. Use named enum members in calculations that receive
already-converted categories.

Choose `pdn.lookup_float` for a read that must produce a float. Use the raw
lookup form when the actual scalar type matters. When changing the spelling of
a formula, compare the full policy outputs and the generated native admission
for any performance-critical Cells.

In live modelx, changing a Reference triggers dependency invalidation. For an
exported or compiled model, create a fresh model instance or process and install
changed inputs before requesting its first calculation.
