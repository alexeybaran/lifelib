# MYGA DV01/CS01 with shared inputs

This experiment replaces the retained demo's portfolio path-preparation routines
with a normal model graph. It is not a new economic model or a compiler backend.

`build_model(route="collect")` uses the existing `collect().sum`/`individual`
contract. `build_model(route="direct")` uses ordinary dynamic policy Spaces and
explicit model-defined portfolio loops. Both use the same policy and assumption
formulas. Benchmark roots are added by the toolkit, not shipped as product Cells.

## Inputs and ownership

- `Data` holds a policy table and four shared assumption tables, loaded once at
  construction. Alternatively supply a policy DataFrame indexed by `point_id`.
- `Data` also holds annual curves/spreads; monthly interpolation is a cached Cell.
- `Scenarios(valuation_month, forward_project, shock)` owns common curve-derived
  rates and discount factors. Its `rate(t, tenor)` has no policy parameter.
- Data lookup Cells cache assumption values by their true keys (age/sex, schedule/month, remaining term). Policy Cells read these shared values and calculate duration-dependent assumptions.
  They do not allocate arrays of prepared paths for all policies.
- `Initial[policy_id]` calculates issue state, bound as `initial_state` in each projection. Actual evolves each policy separately.
- `StateSource` exposes the detached Actual snapshots in collect mode, or ordinary
  cached policy states in direct mode. Valuation consumes those states at months
  0, 12 and 24. Shared market inputs never substitute for independent policy state.

Inputs represent a run snapshot. Replace inputs and clear/rebuild affected model
results using the supported modelx/compiled reset contract before a new run.
Changing a reference does not promise automatic invalidation of completed caches.
There are no file reads during projection or per-policy input-preparation callbacks.

## Economic conventions retained

Actual covers 36 months. Annual valuations use 480 relative periods, with absolute
policy duration continuing from the valuation month. The demo's 480-month contract
term and five-year guarantee windows remain unchanged. This example is not yet a
parameterized implementation of every MYGA policy term/guarantee duration.

DV01 reruns behavior and cash flows under each of seven +1bp key-rate shocks.
CS01 rediscounts the base cash flows under the same triangular discount overlay;
it does not rerun behavior. Curve interpolation, forward rates and arithmetic
come from the retained example. The model is not converted to a different CS01
or DV01 convention during this data-supply redesign.

The small categorical code Cells preserve the demo's existing branch arithmetic.
They are explicit formulas, not hidden portfolio preparation. The original MYGA
lookup helpers supply tables and interpolation consistently in live/export/Cython.

## Verification populations

Live/export references use seven policies only. Compiled scaling uses 105 unique
IDs with 15 repeats of the seven economic rows. Each policy calculates its own
results; only assumptions and market calculations are shared. Expected summed
outputs scale by 15, while individual state snapshots repeat unchanged.

All files in this package are experimental on `experiment/dv01-shared-data`.
Preserved original demo sources, archived outputs and compiler branches are controls.
