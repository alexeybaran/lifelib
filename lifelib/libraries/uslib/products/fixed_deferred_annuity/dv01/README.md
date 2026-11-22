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

## Read the market call

In Market(as_of_month=36, scen_id=1, shock=-1), rate(tenor_month=60, forward_month=60) means “at month 36, price a five-year investment that starts at month 60 and ends at month 120 on path 1.” The two 60s describe different things. A fixing observed at month 60 instead uses Market(as_of_month=60, scen_id=1, shock=-1), with the same rate arguments.

Write P(i,j) for the selected path's price at month i of one dollar payable at month j. The annual-effective quote for a term of n months starting at f is

    (P(i,f) / P(i,f+n)) ** (12 / n) - 1

For an observation at the start of the term, f equals i and the numerator is one. For a future fixing, both prices come from the same curve observed at i. This keeps the valuation independent of future simulated observations. For a key-rate shock the same calculation uses the two bumped bond prices, with the bump weights assigned by time to maturity from i.

## Follow one five-year rollover

| Policy month | Rate decision |
| --- | --- |
| 0 through 59 | Read the issued annual rate from the MYGA policy row. New market observations during this period do not trigger a reset. |
| 60, seen from month 36 | Project the first renewal. Use the month-36 curve for months 60 and 120. Apply the MYGA renewal spread and guaranteed minimum. |
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

At month 36, the five-year key has weight zero on the start bond (24 months to maturity) and 0.6 on the end bond (84 months to maturity, between the 60- and 120-month keys). A one-basis-point bump changes the end price to 0.822793165. The month-60 renewal projected at month 36 rises to 3.046622%. When the valuation starts at month 60 instead, the booked rate of 2.762051% applies to both shock arms. The issued 4.45% and booked 2.762051% correspond to monthly interest rates of 0.363478% and 0.227308% respectively.

## Follow the Cells in the assembled model

From the repository root, import the builder and read a generated path:

```python
from lifelib.libraries.uslib.products.fixed_deferred_annuity.dv01 import build_model

m = build_model(route="direct")
try:
    a = m.Actual(1, 1)                      # policy_id, scen_id
    v = m.Valuation(36, 1, 1, -1)           # valuation_month, policy_id, scen_id, shock
    bumped = m.Valuation(36, 1, 1, 3)       # five-year key
    assert a.credit_rate(0) == a.declared_rate_initial()
    print(v.redeclare_month(61))            # 60
    print(v.renewal_quote(60))              # Market(36, 1, -1).rate(60, 60)
    print(v.credit_rate(61), bumped.credit_rate(61))
    print(a.credit_rate(60))                # Market(60, 1, -1).rate(60, 60)
finally:
    m.close()
```

1. The Data model point supplies the initial declared rate and the guaranteed minimum. MYGA's redeclare_month(t) determines which declaration applies at policy month t. Annual redeclaration switches to twelve-month resets after the first guarantee.
2. Actual.market(t) selects Market(t, scen_id, -1). At a renewal Actual.renewal_quote(t) asks for rate(tenor_month, t). Market.base_price(j) selects the scenario's entry from ESG.P_t_T(t, j). Public path 1 selects array element 0. The ESG synthesizes each bond price from the input curve and the two simulated factors at t.
3. Valuation.market() selects Market(valuation_month, scen_id, shock). Valuation.credit_rate(t) checks the declaration month first. A declaration on or before the cut belongs to Actual. A future declaration uses Valuation.renewal_quote(start) and takes the larger of the guaranteed minimum and the quote less the renewal spread. For the shipped policies the spread is zero.
4. MYGA's credit_rate_mth(t) converts the annual rate. inv_income_pp(t) multiplies the monthly rate by av_pp_at(t, AvTiming.BEF_INV), the balance after withdrawal. This feeds the closing account value and subsequent benefits. Valuation.cashflow_at_offset(k) evaluates net_cf(valuation_month + k). Valuation.discount_factor(k) discounts this month-end amount using Market.price(valuation_month + k + 1).
5. On the collect route Outer.base_liability_pv(month, scen_id) calls Valuation.collect(month, scen_id, -1).sum.liability_pv across policies. Outer.shocked_liability_pv(month, scen_id, key) repeats this on the same economic path with the selected bump. Outer.dv01(month, scen_id, key) subtracts the latter result from the former. Outer.cs01 holds the base cash flows fixed and applies the changed discounts.

CashValue_ME_G2PP extends each policy over every ESG scenario in a vectorized projection, including its certainty-equivalent reference in row 0. This DV01 example makes the stochastic path an explicit argument: results(m, scen_id=1) reports path 1. Outer.scenario_ids() lists the generated paths. A stochastic mean requires aggregating the pathwise results over the selected IDs.
