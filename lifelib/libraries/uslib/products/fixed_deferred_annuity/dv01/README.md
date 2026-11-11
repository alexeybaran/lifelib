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
use the same Scenario ItemSpace. Actual and Valuation own independent policy
state. `StateSource` supplies Actual snapshots to Valuation.

Curve calculations use the original annual-effective rates, piecewise-flat
forward interpolation, end extrapolation and triangular key-rate shocks.
CS01 uses the shared discount factors with the base cash flows. Curve
customizations can be made through the `Curves` Cell formulas.

The default inputs are the CSV files in the parent product directory.
`reference_dir` selects another input directory, and `policy_table` supplies
an alternative policy DataFrame indexed by `point_id`. The source reference
pins are recorded in `provenance.json`.

Pass `myga_model=path_to_saved_MYGA_US_S` to use the saved MYGA model's Data
Cells. DV01 uses those Cells for policy rows and assumption tables and keeps
its own valuation, shock and state formulas. `reference_dir` can select the
CSV directory for those Cells. With this option, the policy book comes from
the MYGA model point Cell.

Export with `model.export(path)` and use the ordinary modelx-cython sample
tracing workflow. The compiler discovers types through the sample run.
