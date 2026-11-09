# Explicit expression streams (development contract)

These helpers are ordinary Python functions with direct Cython `.pxd` provider
declarations. The compiler binds declared helper symbols and signatures. It does
not parse generator expressions or inspect lambda bodies to recognize them.
This development API is not yet a qualification of all regional models.

```python
sum_float(periods(proj_len()), lambda t: net_cf(t) * disc(t))
sum_float(periods(proj_len()), lambda t: claims(t),
          where=lambda t: pols_if(t) > 0.0)

# Same map/filter engine, composed explicitly.
sum_float(over(periods(proj_len()), lambda t: net_cf(t) * disc(t)))

all(over(periods(proj_len()), lambda t: check_balance(t)))
next(over(zip(ages[:-1], ages[1:]), lambda p, q: (p, q),
          where=lambda p, q: p <= age <= q, unpack=2))

# One flat contribution sequence; no sum of inner sums.
sum(flatten(over(periods(1, 6), lambda g:
    over(periods(1, karenz_months() + 1), lambda z: pols_karenz(t, g, z)))))
```

## Small vocabulary

| Helper | Contract |
|---|---|
| `periods(start, stop=omitted, step=omitted)` | Reusable `range` domain; one, two or three supplied arguments have `range` values, integer conversion order and zero-step behavior. Optional arguments may be named. |
| `over(source, function, where=None, *, unpack=None)` | One-shot lazy stream. Acquire `iter(source)` at construction. For each candidate, unpack if requested, evaluate the predicate, then the payload once. |
| `flatten(sources)` | One-shot lazy concatenation. Acquire the outer iterator at construction; acquire each inner iterator only when reached. |
| `sum_float(source, function=omitted, where=None) -> float` | Lazily convert each passing contribution with standard `float`, then sum the resulting doubles using float-start summation. Empty input is float `0.0`. |
| `sum_values(source)` | Compatibility spelling for ordinary builtin `sum(source)`, including empty integer zero, arbitrary integers and custom/NumPy arithmetic. Prefer ordinary `sum` in authored formulas. |

`sum_float` is precisely `sum((float(value) for value in source), 0.0)` with
the standard builtin bindings. Its shorthand first creates the canonical
map/filter stream. It does not consult a replaced public `over` binding.
An explicitly authored `sum_float(over(...))` does consult that current binding.
`sum_float` differs from ordinary `sum` and from `sum(values, 0.0)` for some
integer prefixes, NumPy scalars, Decimal and custom numeric objects. Migration
requires proof of the original supported numeric domain; a float-looking sample
does not justify replacing an ordinary sum.

With only `where=`, `sum_float(source, where=eligible)` filters source values
before float conversion. Explicit `function=None` supplies a non-callable; it
does not mean omission. `periods(start=5)` is the one-bound domain 0 through 4;
`periods(stop=5)` lacks its required first bound. The named three-bound form is
`periods(start=0, stop=5, step=2)`.

Existing Python consumers remain useful: `all`, `any`, `min`, `max`, `next`,
`sorted`, `tuple`, `list`, `set`, and `dict`. Their original short circuit,
identity, tie, ordering and materialization contracts apply. Keep eager lists
eager before passing them to pandas. Their native coverage is proved separately
from the stream provider; the presence of these expressions is not a receipt.

`unpack=N` is explicit because a tuple may itself be one intended callback
argument. It accepts a nonnegative exact Python integer. Unpacking runs before
the predicate, requires exactly N elements and reads at most N+1 values. Too
few/many elements produce `ValueError`, rather than callback arity errors.
Payload and predicate receive the unpacked arguments in the same order.

## Laziness, exceptions and mutable bindings

Bounds are evaluated at the authored call position. Inner dependent bounds
remain inside the outer callback. Preserve original nesting and filter order;
do not prebuild a Cartesian product or change flat summation into inner sums.
Use lambdas for on-demand Cell/Reference lookup. Passing a Cell itself as the
callback captures its callable earlier and is not always an equivalent edit.

Natural source exhaustion finishes with plain `StopIteration`, value None,
without source exception context. A payload, predicate, unpack acquisition, or
inner-iterator acquisition that raises `StopIteration` is inside the generator
body boundary: raise `RuntimeError('generator raised StopIteration')` with the
original exception as cause/context. Other exceptions preserve identity and
close that producer. Streams stay exhausted after a body failure.

Consumer-side failures do not close an externally retained suspended producer.
In particular, `sum_float` conversion belongs to its private normalization
layer. Conversion failure leaves a retained upstream `over` stream resumable;
a conversion `StopIteration` is wrapped at the normalization boundary.

All registered public dispatchers return objects and receive the current
callable first. Replacement callables receive the actual original positional
and keyword argument layout and may return any object. Only the canonical
`sum_float_kernel` has a double ABI. Neither Reference replacement nor callback
creation grants permission to freeze future Cell/Reference values.

## Actual Cython typing

An ordinary lambda calling declared typed Cells can use native Cell entries and
C numeric arithmetic, with boxing/unboxing at its callable boundary. A compiled
lambda alone is not proof. For direct scalar arithmetic needing an explicit
input type, ordinary named Cython-annotated callbacks are available:

```python
def contribution(t: cython.longlong) -> cython.double:
    return 1.0 + t * 0.5
return sum_float(periods(n), contribution)
```

The normal model exporter must preserve these declarations and the compiler's
Cell override checks. Stock Cython does not turn an arbitrary capturing lambda
into a fully unboxed C function pointer through a helper wrapper. Generated
Cython/C and runtime binary identities must substantiate each native path.

The range cursor has a header-only int64 fast domain with checked admission and
overflow-safe termination. Wide range endpoints retain their exact Python range
semantics through compatibility iteration. Arbitrary source iterators and Python
callbacks also retain compatibility behavior. These paths are tested, but do
not complete a native coverage row.

Current evidence is a provider/binding checkpoint. Full regional source
integration, transitive typed payload/domain coverage, financial differentials,
operation matrix reconciliation and matched timing remain required.
The surrounding compiler Cell return/cache ABI also remains a gate: a traced
double Cell can still coerce an object returned by a replaced helper after the
provider has preserved it. Empty ordinary sums can similarly expose integer
versus float report dtypes. The local architecture owner must resolve that
generic boundary; provider tests alone do not qualify it.
