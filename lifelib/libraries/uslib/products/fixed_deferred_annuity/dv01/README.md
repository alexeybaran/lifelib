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

## From the observed fixing to one policy's DV01

This live direct calculation uses shipped policy 1 alone, generated path 1, cut month 60, a +1 bp shock at key 3 (five years), and 480 monthly cash-flow offsets. Actual has already fixed the current rollover rate. The next rollover is at policy month 120.

| Cell or result | Base | Five-year key bumped |
| --- | ---: | ---: |
| Market(60,1,shock).rate(60,60), the current spot | 2.762051% | 2.772051% |
| Valuation(60,1,1,shock).credit_rate(60), booked by Actual | 2.762051% | 2.762051% |
| Market(60,1,shock).price(120), price for start of next term | 0.872642126 | 0.872217656 |
| Market(60,1,shock).price(180), price for end of next term | 0.760771737 | 0.760771737 |
| Valuation.credit_rate(120), next projected declaration | 2.781834% | 2.771833% |
| Valuation.inv_income_pp(121), interest per in-force contract | $314.35 | $313.23 |
| Valuation.av_pp(121), closing balance per in-force contract | $137,636.49 | $137,634.26 |
| Valuation.net_cf(121), projected monthly net cash flow | −$1,524.9833 | −$1,524.9587 |
| Valuation.discount_factor(61), month-60 price to end of month 121 | 0.868507702 | 0.868085729 |
| Outer portfolio liability on this one-policy book | $104,844.93667 | $104,807.01246 |

The month-120 forward falls when the five-year key rises because only the forward-start bond sits at the bumped node. The end bond is ten years away and has zero weight on the five-year key. If Actual subsequently runs to month 120, its own spot fixing on the realized path is 3.523481%; that later observation is unavailable to a month-60 valuation.

Outer.dv01(60,1,3) returns **$37.92421**. Outer.cs01(60,1,3) returns **$4.20828** for frozen base cash flows. The difference includes every cash-flow response to the shock, including behavior and MVA effects.

Run the [worked example](worked_example.py) to reproduce the [recorded values](worked_example.json). The default workbook resolves from the installed lifelib distribution containing the G2++ example. Supply an alternative workbook explicitly when using a different calibration. Native qualification uses locked_spaces=["ESG", "Market"] for shared market calculations.
