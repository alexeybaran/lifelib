# MYGA key-rate DV01 on generated interest-rate paths

A crediting rate is a policy promise. The market curve supplies a quote when that promise resets. Between resets the policy keeps the declared rate even as market rates move.

| Space | What it owns |
| --- | --- |
| Data | MYGA policy rows and actuarial assumptions, including the issued guarantee, floor and withdrawal assumptions. |
| ESG | The input curve, G2++ parameters and random draws. Its bond-price Cell returns one value per generated path. |
| Market | One valuation date, one generated path and one key-rate shock. Turns conditional bond prices into spot or forward annual-effective rates. |
| Actual | One policy on one generated path. Advances month by month, applying observed rates when the contract resets. |
| Valuation | One policy restarted from Actual at a specified date. Carries booked rates and projects future resets from that date's curve. |
| Outer | Collects policy cash flows on the same path and compares base and shocked liabilities. |

## Annual DV01 and CS01 DataFrames

```python
from lifelib.libraries.uslib.products.fixed_deferred_annuity.dv01 import build_model

model = build_model(valuation_months=range(0, 121, 12))
try:
    dv01, cs01 = model.Outer.annual_risk_report(num_scenarios=2, annual_steps=10)
finally:
    model.close()
```

Each frame has one row per `(scenario, year)` and one column per key-rate tenor
in months from `shock_steps.csv`. Ten annual steps give eleven closes,
from year 0 through year 10. Zero steps gives just the issue-date close.
Scenarios are individual generated ESG paths numbered from 1. Each value is
the portfolio liability change for a +1 bp shock, using the corresponding
Outer Cell and its sign convention. The compiler sample calls this Outer Cell at year zero. The exported
model exposes the same Cell.

## Read the nine Actual outputs at a valuation date

The individual results of `Actual.collect(scen_id)` carry the nine columns of
the annual policy report. For example, at a configured snapshot month `c`,
`actuals.individual[policy_id].credit_rate[c]` gives the booked annual rate.
Valuation calls the same financial Cell name on both routes. For example,
`act.mgsv_pp(72)` calls Actual's Cell in direct mode. In collect mode it
reads the detached `mgsv_pp` series at key 72, the same value as `mgsv_pp[72]`. A cut
at policy month 72 includes that month's closing cash flow and balances.
The first prospective cash flow is month 73, paid on grid date 74 and
discounted to grid date 73. The annual report still describes the opening
of each labelled policy month.

Valuation uses one Market for every rate request. For a month-72 close,
`v.market().rate(60, 72)` reads the observed five-year spot rate on the
selected ESG path at month 72, even on a shocked Valuation.
`v.market().rate(60, 73)` reads the five-year spot rate from the selected
month-73 curve, including its bump. `v.market().rate(60, 120)` reads the
five-year forward starting in month 120 from that same curve. A crediting
rate fixed before the close comes directly from Actual until its next reset.

| Valuation historical Cell at month t | Field of the collected policy |
| --- | --- |
| `av_pp(t)` | `av_pp[t]` |
| `mgsv_pp(t)` | `mgsv_pp[t]` |
| `interest_credited_pp(t)` | `interest_credited_pp[t]` |
| `prem_accum_gmir_pp(t)` | `prem_accum_gmir_pp[t]` |
| `pols_if(t)` | `pols_if[t]`, including the first projected month's opening |
| `free_wd_remain(t)` | `free_wd_remain[t]` |
| `tax_basis_pp(t)` | `tax_basis_pp[t]` |
| `net_cf(t)` | `net_cf[t]` |
| `credit_rate(t)` | `credit_rate[min(t, valuation_month)]` for an observed redeclaration |
| `mva_ref_yield_locked(t)` | `mva_ref_yield_locked[min(t, valuation_month)]` for an observed fixing |

The last three additional histories required alongside the annual report
are the remaining free withdrawal allowance, closing tax basis and individual cash flow.
Two annual columns, policy-year-to-date interest and the free withdrawal
allowance before the month's withdrawal, serve reporting. Valuation uses
cumulative credited interest and the allowance left after the withdrawal.
For a cut beyond the configured snapshots, Actual collects through the requested month.

## Configure key-rate shocks

Edit [shock_steps.csv](../shock_steps.csv) in the input book before starting a fresh run. The tenor_months column accepts positive whole months in strictly increasing order, one maturity per row. The shipped grid is annual through year 10, then years 15 and 20. Index 0 selects the first row; -1 selects the base. The bump is +1 bp at the selected tenor, with linear interpolation to adjacent keys. Data.shock_key_months() caches the CSV once per model. Supply the revised book to the same compiled model in a fresh process. Resolve key indices by tenor when changing grids. When compiling Outer, set its cells_param_size for key to 2147483647 so the sampled key count does not become a runtime limit. The compiler uses a hash cache for this domain.

## Read the market call

In Market(as_of_month=36, scen_id=1, shock=-1), rate(tenor_month=60, forward_month=60) means “at month 36, price a five-year investment that starts at month 60 and ends at month 120 on path 1.” The two 60s describe different things. A fixing observed at month 60 instead uses Market(as_of_month=60, scen_id=1, shock=-1), with the same rate arguments.

Write P(i,j) for the selected path's price at month i of one dollar payable at month j. The annual-effective quote for a term of n months starting at f is

    (P(i,f) / P(i,f+n)) ** (12 / n) - 1

For an observation at the start of the term, f equals i and the numerator is one. For a future fixing, both prices come from the same curve observed at i. This keeps the valuation independent of future simulated observations. For a key-rate shock the same calculation uses the two bumped bond prices, with the bump weights assigned by time to maturity from i.

## Follow one five-year rollover

| Policy month | Rate decision |
| --- | --- |
| 0 through 59 | Read the issued annual rate from the MYGA policy row. New market observations during this period do not trigger a reset. |
| 60, seen from month 36 | Project the first renewal. Use the month-37 curve after the close of month 36 for months 60 and 120. Apply the MYGA renewal spread and guaranteed minimum. |
| 60, seen from month 60 | Actual observes the five-year spot on its generated path and books the new rate. The restart is after this fixing. Base and shocked Valuations both inherit it. |
| 61 through 119 | The declaration month is still 60. A Valuation restarted after the fixing uses the rate that Actual booked. |
| 120 | The rollover policy resets again. For annual redeclaration, the corresponding next reset after 60 is 72, and the renewal market tenor is 12 months. |

The annual declared rate flows into MYGA's monthly interest and account-value formulas. A higher prospective renewal can change cash flows through credited interest and policyholder behavior. Key-rate DV01 also includes the effect of applying the shocked discount factors to the resulting cash flows. For each path, the signed result is the base liability less the revalued shocked liability.

## Reproduce the fixing by hand

The upstream example workbook selects EUR_BASE, seed 1234 and 1,000 antithetic scenarios. Policy 1 is the five-year rollover row of model_point_table.csv. These inputs illustrate rate-setting mechanics on a generated path. A US-dollar risk result requires the relevant US-dollar curve and calibration.

| Observation date | Start | End | Path 1 start price | Path 1 end price | Five-year annual quote |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 36 | 60 | 120 | 0.956003501 | 0.823129320 | 3.038204% |
| 60 | 60 | 120 | 1.000000000 | 0.872642126 | 2.762051% |
| 60 | 120 | 180 | 0.872642126 | 0.760771737 | 2.781834% |

Key-rate indices 0 through 11 correspond to maturities of 1 through 10, 15 and 20 years. For a market observed at grid date 36 the two bonds for the month-60 renewal mature in two and seven years, each on its own key. Both have zero weight on the five-year key. When the valuation starts at month 60 instead, the booked rate of 2.762051% applies to both shock arms. The issued 4.45% and booked 2.762051% correspond to monthly interest rates of 0.363478% and 0.227308% respectively.

## Follow the Cells in the assembled model

From the repository root, import the builder and read a generated path:

```python
from lifelib.libraries.uslib.products.fixed_deferred_annuity.dv01 import build_model

m = build_model(route="direct")
try:
    a = m.Actual(1, 1)                      # policy_id, scen_id
    v = m.Valuation(36, 1, 1, -1)           # valuation_month, policy_id, scen_id, shock
    bumped = m.Valuation(36, 1, 1, 4)       # five-year key
    assert a.credit_rate(0) == a.declared_rate_initial()
    print(v.redeclare_month(61))            # 60
    print(v.renewal_quote(60))              # Market(37, 1, -1).rate(60, 60)
    print(v.credit_rate(61), bumped.credit_rate(61))
    print(a.credit_rate(60))                # Market(60, 1, -1).rate(60, 60)
finally:
    m.close()
```

1. The Data model point supplies the initial declared rate and the guaranteed minimum. MYGA's redeclare_month(t) determines which declaration applies at policy month t. Annual redeclaration switches to twelve-month resets after the first guarantee.
2. Actual.market(t) selects Market(t, scen_id, -1). At a renewal Actual.renewal_quote(t) asks for rate(tenor_month, t). Market.base_price(j) selects the scenario's entry from ESG.P_t_T(t, j). Public path 1 selects array element 0. The ESG synthesizes each bond price from the input curve and the two simulated factors at t.
3. Valuation.market() selects Market(valuation_month + 1, scen_id, shock). Valuation.credit_rate(t) checks the declaration month first. A declaration on or before the cut belongs to Actual. A future declaration uses Valuation.renewal_quote(start) and takes the larger of the guaranteed minimum and the quote less the renewal spread. For the shipped policies the spread is zero.
4. MYGA's credit_rate_mth(t) converts the annual rate. inv_income_pp(t) multiplies the monthly rate by av_pp_at(t, AvTiming.BEF_INV), the balance after withdrawal. This feeds the closing account value and subsequent benefits. Valuation.cashflow_at_offset(k) evaluates net_cf(valuation_month + k + 1). Valuation.discount_factor(k) discounts this month-end amount using Market.price(valuation_month + k + 2).
5. On the collect route Outer.base_liability_pv(month, scen_id) calls Valuation.collect(month, scen_id, -1).sum.liability_pv across policies. Outer.shocked_liability_pv(month, scen_id, key) repeats this on the same economic path with the selected bump. Outer.dv01(month, scen_id, key) subtracts the latter result from the former. Outer.cs01 holds the base cash flows fixed and applies the changed discounts.

CashValue_ME_G2PP extends each policy over every ESG scenario in a vectorized projection, including its certainty-equivalent reference in row 0. This DV01 example makes the stochastic path an explicit argument: results(m, scen_id=1) reports path 1. Outer.scenario_ids() lists the generated paths. A stochastic mean requires aggregating the pathwise results over the selected IDs.

## Month-120 crediting rate with the shock applied at month 72

Policy 1 on stochastic path 1 rolls over every 60 months. Actual books 2.762051% at month 60. At the month-72 cut both arms inherit this rate through month 119. At month 120, redeclare_month(120) returns 120, which is later than the cut. The future declaration is priced from grid date 73, at the close of policy month 72.

```python
base = m.Valuation(72, 1, 1, -1)  # valuation_month, policy_id, scen_id, shock
bump = m.Valuation(72, 1, 1, 4)   # +1 bp at the five-year key
bump.credit_rate(120)
# redeclare_month(120) -> 120
# renewal_quote(120) -> Market(73, 1, 4).rate(tenor_month=60, forward_month=120)
# credit_rate(120) -> max(gmir(), renewal_quote(120) - renewal_crediting_spread(120))
```

Market takes the path-1 entries from ESG.P_t_T(73,120) and ESG.P_t_T(73,180). Relative to the cut, the two maturities are 47 and 107 months. Both have zero weight under the five-year shock. The annual-effective forward is the fifth root of the start price divided by the end price, minus one.

| Month-72 valuation of policy 1 | Base | Five-year bump |
| --- | ---: | ---: |
| Market.price(120) | 0.864506563 | 0.864506563 |
| Market.price(180) | 0.727501943 | 0.727501943 |
| Valuation.credit_rate(119), declaration booked in Actual | 2.762051% | 2.762051% |
| Valuation.credit_rate(120), new annual declaration | 3.511077% | 3.511077% |
| Valuation.credit_rate_mth(120) | 0.287984% | 0.287984% |
| Valuation.inv_income_pp(120) | $394.56294 | $394.56294 |

The shipped spread is zero and the 0.25% guaranteed minimum is below both forward quotes. For the one-policy valuation through contract maturity, Outer.dv01(72,1,4) is $0.27130 (base liability $10,220.32497 less shocked $10,220.05367). This includes all projected cash-flow and discounting changes.

Each policy projects through its own final contract month. Direct and Collect return portfolio cash flows for the remaining term of the longest policy at each close. The rectangular report produced by `results()` pads shorter rows with zeros.

Run the [worked example](worked_example.py) to reproduce the [recorded values](worked_example.json). The default workbook resolves from the installed lifelib distribution containing the G2++ example. Supply an alternative workbook explicitly when using a different calibration. Native qualification uses locked_spaces=["ESG", "Market"] for shared market calculations.

The [native compilation spec](native_spec.py) sizes the two arguments of `Market.rate(tenor_month, forward_month)` separately. On the shipped five-year policies the tenor runs from 0 through 60 months, and the forward month uses the same 0 through 1,201 range as the policy calculation. The 73,322-slot dense budget applies only to this Cell. Discount prices and shock weights keep their separate curve-length ranges. Regenerate the spec if a new policy book introduces longer guarantee periods. Changing the shock-step CSV within the curve domain does not widen the policy quote tenor.

Tenors are integer months. At policy month 1 of a five-year rollover contract the competitor quote has 59 months remaining. The end-of-month MVA quote has 58. Both are taken from the curve at forward month 1.
