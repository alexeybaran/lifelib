"""Print a path-1 MYGA renewal and valuation walkthrough as JSON.

From the repository root, run
`python -m lifelib.libraries.uslib.products.fixed_deferred_annuity.dv01.worked_example`.
Rates in the JSON are decimal fractions. The shipped ESG workbook and policy
record are used unchanged.
"""

import json
from pathlib import Path

import pandas as pd

from .model import build_model


def observe(actual, engine, scenario, month):
    return {
        'opening_av': actual.policy_state(month)[0],
        'in_force': actual.pols_if(month),
        'booked_credit': actual.credit_rate(month),
        'booked_mva_yield': actual.mva_ref_yield_locked(month),
        'engine_price_5y': float(engine.P_t_T(month, month + 60)[scenario - 1]),
        'spot_5y': actual.market(month).rate(60, month),
    }


def project(item, cut, reset, month):
    market = item.market()
    offset = month - cut
    cashflow = item.cashflow_at_offset(offset)
    discount = item.discount_factor(offset)
    return {
        'price_to_reset': market.price(reset),
        'price_to_reset_plus_60': market.price(reset + 60),
        'cut_5y_spot': market.rate(60, cut),
        'cut_booked_credit': item.credit_rate(cut),
        'cut_booked_mva_yield': item.mva_ref_yield_locked(cut),
        'reset_5y_forward': item.renewal_quote(reset),
        'reset_spread': item.renewal_crediting_spread(reset),
        'gmir': item.gmir(),
        'reset_credit': item.credit_rate(reset),
        'next_month_locked_mva_yield': item.mva_ref_yield_locked(month),
        'next_month_credit': item.credit_rate_mth(month),
        'next_month_opening_av': item.av_pp_at(month, item.AvTiming.BEF_WD),
        'next_month_interest': item.inv_income_pp(month),
        'next_month_closing_av': item.av_pp(month),
        'next_month_competitor_tenor_months': item.competitor_tenor(month),
        'next_month_competitor_rate': item.market_rate(month),
        'next_month_mva_tenor_months': round(12 * item.mva_term(month)),
        'next_month_current_mva_rate': item.mva_ref_yield(month),
        'next_month_net_cashflow': cashflow,
        'next_month_discount': discount,
        'next_month_liability_pv': -cashflow * discount,
    }


def run():
    policy, scenario, shock = 1, 1, 3
    cut, reset, report_month = 60, 120, 121
    folder = Path(__file__).resolve().parents[1]
    policies = pd.read_csv(folder / 'model_point_table.csv', index_col='point_id').loc[[policy]]
    model = build_model(route='direct', policy_table=policies, outer_months=122,
                        valuation_months=(12, cut, reset))
    try:
        engine = model.ESG
        actual = model.Actual(policy, scenario)
        base = model.Valuation(cut, policy, scenario, -1)
        bumped = model.Valuation(cut, policy, scenario, shock)
        outer = model.Outer
        return {
            'policy': policies.loc[policy, 'policy_id'],
            'scenario': scenario,
            'engine_parameters': engine.param_table().to_dict(),
            'actual_horizon_months': len(model.Actual.projection_months),
            'valuation_horizon_months': len(model.Valuation.projection_months),
            'cut_month': cut,
            'reset_month': reset,
            'projection_month': report_month,
            'reporting_offset': report_month - cut,
            'payment_maturity_month': report_month + 1,
            'shock_index': shock,
            'shock_bp': 1,
            'actual_month_12': observe(actual, engine, scenario, 12),
            'actual_month_60': observe(actual, engine, scenario, cut),
            'actual_month_120': observe(actual, engine, scenario, reset),
            'month_60_credit_projected_from_month_36': model.Valuation(
                36, policy, scenario, -1).credit_rate(cut),
            'base': project(base, cut, reset, report_month),
            'bumped': project(bumped, cut, reset, report_month),
            'one_policy_outer': {
                'base': outer.base_liability_pv(cut, scenario),
                'shocked': outer.shocked_liability_pv(cut, scenario, shock),
                'dv01': outer.dv01(cut, scenario, shock),
                'cs01': outer.cs01(cut, scenario, shock),
            },
        }
    finally:
        model.close()


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
