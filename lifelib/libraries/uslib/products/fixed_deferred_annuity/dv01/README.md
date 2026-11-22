# Shared MYGA DV01 and CS01 model

Create a live model with `build_model(route="collect")` or
`build_model(route="direct")`. `results(model)` returns base liability values,
DV01, CS01, base valuation cash flows, Actual cash flows and annual state
snapshots. Close the model after use.

`Data` owns the policy and assumption tables and the annual market inputs.
`Curves` owns monthly interpolation, prepared node discount factors, base
zero yields and discount factors. Its keys describe the curve observation,
annual or monthly input selection, maturity and shock. Base curve preparation
and base yields are shared across shocks.

`Scenarios(valuation_month, forward_project, shock)` delegates market
calculations to `Curves`. All policies at the same valuation date and shock
use the same Scenario ItemSpace by default. Actual runs the saved MYGA
calculations at absolute policy months. Each Valuation item owns a canonical
MYGA contract child. The child uses Actual history for state observed by the
cut and projects the suffix with the market supplied by its parent's
`market()` Cell. The public Valuation cash-flow and discount Cells take
months relative to the cut.

Curve calculations use the original annual-effective rates, piecewise-flat
forward interpolation, end extrapolation and triangular key-rate shocks.
CS01 uses the shared discount factors with the base cash flows. Curve
customizations can be made through the `Curves` Cell formulas. An item-level
Valuation market override applies to that item's prospective rates and
discounting. The initial declared credit rate and the MVA reference fixing
come from the issued policy record.

Data is the converted MYGA_US_S Data Space (its table Cells read the CSV files) with
the DV01 lookup Cells written as plain table reads, as the MYGA Projection reads the
same tables: `.loc` by key, a missing withdrawal or surrender key is zero, the MVA
factor is interpolated between whole years and held beyond the last row. The
shared readers cache each assumption table as it is used.

The default inputs are the CSV files in the parent product directory.
`reference_dir` selects another input directory, and `policy_table` supplies
an alternative policy DataFrame indexed by `point_id`. The source reference
pins are recorded in `provenance.json`.

Pass `myga_model=path_to_saved_MYGA_US_S` to use the saved MYGA model's Data
Cells. DV01 uses those Cells for policy rows and assumption tables and uses the
saved Projection Cells for the underlying actuarial calculations. DV01 supplies
its market roles, observed Actual history, and valuation and shock orchestration.
`reference_dir` can select the CSV directory for those Cells. With this option,
the policy book comes from the MYGA model point Cell.

Export with `model.export(path, locked_spaces=['Scenarios'])` and use the
ordinary modelx-cython sample tracing workflow. The compiler discovers types
through the sample run. The lock protects shared Scenario calculations while
policy items in Actual and Valuation remain independently eligible for collect.

## Follow one valuation

```text
Model
├── Data                         MYGA tables and DV01 annual curve and spread inputs
├── Curves                       monthly interpolation and key-rate mathematics
├── Scenarios(month, forward_project, shock)
├── Actual(policy_id)            observed history and booked rates
├── Valuation(month, policy_id, shock)
│   └── ValuationContract        MYGA calculations on the policy clock
└── Outer                        policy totals, DV01 and CS01
```

The builder sets the example's ten annual observations on Data. At year zero
all seven tenors are at 1%, and at year one they are at 2%. The crediting
spread rises from 0.50% to 1.50% across the ten observations.
`Curves.monthly_inputs()` interpolates between observations for Actual.
For example, the observed curve at month six is 1.50% at every tenor.

```python
v = model.Valuation(12, 7, 3)
market = v.market()
assert market is model.Scenarios(12, True, 3)
assert v.ValuationContract.market() is market
assert model.Valuation(12, 8, 3).market() is market
```

At this valuation date the base curve is 2%. Shock index 3 bumps the
five-year node to 2.01%. At local month zero, `market.rate(0, 5.0)`
therefore returns 2.01%. At local month six, the contract is at policy
month 18. New quotes use the forward curve starting six months after the
valuation. A rate already booked by month 12 comes from Actual history.

```python
base = model.Valuation.collect(12, -1).sum.liability_pv
shocked = model.Valuation.collect(12, 3).sum.liability_pv
dv01 = base - shocked
```

Each liability discounts its own projected cash flows. CS01 holds the
base cash flows fixed and applies the shocked discount factors. The
standard book runs one Actual projection per policy and eight Valuations
at each of months 0, 12 and 24.

## Checking results

A book made of k copies of the seven reference policies must give k times the
seven-policy results. Each element may differ by

    1e-10 x (the sum of the magnitudes that went into the value) + 1e-7

For a plain sum, that sum of magnitudes is |value|. DV01 and CS01 are a base
present value minus a shocked present value, both totals over the book. Their
sum of magnitudes is |base PV| + |shocked PV|, because the difference is much
smaller than either term and inherits the rounding of both.
