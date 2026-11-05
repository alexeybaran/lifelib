"""DV01 with shared raw data and scenario Cells, for live/export/Cython.

The retained example's Actual/Valuation economic conventions remain unchanged.
No policy-month arrays are prepared before the formula graph executes.
"""
from pathlib import Path
import inspect
import numpy as np
import pandas as pd
from . import lookup
from . import policy, assumptions, scenario, curve_helpers

OUTER_MONTHS = 36
HORIZON = 480
VALUATION_MONTHS = (0, 12, 24)


def actual_formula(policy_id):
    return {'refs': {'initial_state': Initial[policy_id].state(),
                     'Market': Scenarios(0, False, -1)}}


def valuation_formula(valuation_month, policy_id, shock=-1):
    return {'refs': {'initial_state': StateSource.state(valuation_month, policy_id),
                     'Market': Scenarios(valuation_month, True, shock)}}


def initial_state():
    premium = Data.numeric_field(policy_id, 'premium')
    rate = max(Data.numeric_field(policy_id, 'gmir'),
               Scenarios(0, False, -1).rate(0, 5.0) - Scenarios(0, False, -1).spread(0))
    free = (Data.numeric_field(policy_id, 'free_wd_rate') * premium
            if Data.label_field(policy_id, 'free_wd_rule') == 'pct_av' else 0.0)
    return np.array([premium, 0.875 * premium,
                     Data.numeric_field(policy_id, 'pols_if_init'),
                     0.0, 0.0, premium, free, rate,
                     Scenarios(0, False, -1).rate(0, 5.0)], dtype=float)


def build_model(*, model_name='MYGASharedDataDV01', reference_dir=None,
                policy_table=None, route='collect'):
    import modelx as mx
    if route not in ('collect', 'direct'):
        raise ValueError('route must be collect or direct')
    folder = Path(reference_dir or Path(__file__).resolve().parent.parent)
    table = (pd.read_csv(folder / 'model_point_table.csv', index_col='point_id')
             if policy_table is None else policy_table.copy())
    if not table.index.is_unique or len(table) == 0:
        raise ValueError('policy IDs must be nonempty and unique')
    table = table.sort_index()
    ids = tuple(int(i) for i in table.index)
    curves, spreads = curve_helpers.outer_scenario()
    model = mx.new_model(model_name)
    data = model.new_space('Data', refs={
        'policy_table': table,
        'mortality': pd.read_csv(folder / 'mort_table.csv', index_col=['age', 'sex']),
        'withdrawals': pd.read_csv(folder / 'withdrawal_table.csv', index_col=['wd_schedule_id', 't']),
        'surrender': pd.read_csv(folder / 'surr_charge_table.csv', index_col=['schedule', 'contract_year']),
        'mva_factors': pd.read_csv(folder / 'mva_factor_table.csv', index_col='years_remaining'),
        'annual_curves': curves, 'annual_spreads': spreads, 'curves': curve_helpers, 'lookup': lookup})
    data.new_cells('numeric_field', "lambda policy_id, column: lookup.at(policy_table, policy_id, column)")
    data.new_cells('label_field', "lambda policy_id, column: lookup.field(policy_table, policy_id, column)")
    data.new_cells('mortality_rate', "lambda age, sex: lookup.at(mortality, (age, sex), 'mort_rate')")
    data.new_cells('withdrawal_amount', "lambda schedule, month: lookup.get(withdrawals, (schedule, month), 'wd_amount')")
    data.new_cells('surrender_rate', "lambda schedule, year: lookup.get(surrender, (schedule, year), 'surr_charge_rate')")
    data.new_cells('mva_factor_lo', "lambda term: lookup.linear(mva_factors, term, 'factor_lo')")
    data.new_cells('mva_factor_hi', "lambda term: lookup.linear(mva_factors, term, 'factor_hi')")
    data.new_cells('monthly_inputs', """def monthly_inputs():
    return curves.monthly_outer_scenario(annual_curves, annual_spreads, months=36)""")
    data.new_cells('monthly_curves', 'lambda: monthly_inputs()[0]')
    data.new_cells('monthly_spreads', 'lambda: monthly_inputs()[1]')
    market = model.new_space('Scenarios',
        formula=lambda valuation_month=0, forward_project=False, shock=-1: None,
        refs={'Data': data, 'curves': curve_helpers})
    for name, formula in inspect.getmembers(scenario, inspect.isfunction):
        market.new_cells(name, formula)
    initial = model.new_space('Initial', formula=lambda policy_id: None,
        refs={'Data': data, 'Scenarios': market, 'lookup': lookup, 'np': np})
    initial.new_cells('state', initial_state)
    states = model.new_space('StateSource')
    common = {'policy_ids': ids, 'np': np, 'lookup': lookup, 'Data': data,
              'Scenarios': market, 'Initial': initial, 'mva_admin_spread': 0.0025}
    options = {'collect_over': {'policy_id': ids}, 'collect_outputs': lambda: {
        'individual': {'state': {t: policy_state(t) for t in snapshot_months}},
        'sum': {'net_cf': {t: net_cf(t) for t in projection_months}}}} if route == 'collect' else {}
    actual = model.new_space('Actual', formula=actual_formula,
        refs={**common, 'initial_state': np.zeros(9), 'Market': market,
              'valuation_month': 0, 'HORIZON': OUTER_MONTHS,
              'projection_months': tuple(range(OUTER_MONTHS)), 'snapshot_months': VALUATION_MONTHS},
        **options)
    if route == 'collect':
        options = {'collect_over': {'policy_id': ids}, 'collect_outputs': lambda: {
            'sum': {'liability_pv': liability_pv(),
                    'net_cf': {t: net_cf(t) for t in projection_months}}}}
    valuation = model.new_space('Valuation', formula=valuation_formula,
        refs={**common, 'initial_state': np.zeros(9), 'Market': market,
              'StateSource': states, 'HORIZON': HORIZON,
              'projection_months': tuple(range(HORIZON))}, **options)
    for space in (actual, valuation):
        for module in (policy, assumptions):
            for name, formula in inspect.getmembers(module, inspect.isfunction):
                if name in space.cells:
                    space.cells[name].formula = formula
                else:
                    space.new_cells(name, formula)
        fields = {'premium_pp': 'premium', 'gmir': 'gmir', 'mgsv_rate': 'mgsv_rate',
                  'mgsv_charge': 'mgsv_annual_charge', 'free_rate': 'free_wd_rate',
                  'premium_tax': 'premium_tax_rate', 'age_at_entry': 'age_at_entry'}
        for name, column in fields.items():
            space.new_cells(name, f"def {name}():\n    return Data.numeric_field(policy_id, {column!r})")
        for name in ('sex', 'wd_schedule_id', 'renewal_architecture'):
            space.new_cells(name, f"def {name}():\n    return Data.label_field(policy_id, {name!r})")
        space.new_cells('free_exempt', "lambda: Data.numeric_field(policy_id, 'free_wd_mva_exempt')")
        space.new_cells('mgsv_net_wd', "lambda: 1.0 if Data.label_field(policy_id, 'mgsv_wd_convention') == 'net_of_charges' else 0.0")
        space.new_cells('free_rule', "lambda: 0.0 if Data.label_field(policy_id, 'free_wd_rule') == 'pct_av' else 1.0")
        space.new_cells('mva_family', """def mva_family():
    name = Data.label_field(policy_id, 'mva_family')
    return {'linear_duration': 0.0, 'geometric': 1.0, 'declared_differential': 2.0}[name]""")
        space.new_cells('mva_cap', """def mva_cap():
    name = Data.label_field(policy_id, 'mva_cap_rule')
    return {'sym_sc': 0.0, 'min_sc_interest': 1.0, 'asym_sc_snfl': 2.0, 'gmir_floor': 3.0, 'none': 4.0}[name]""")
    states.Actual = actual
    outer = model.new_space('Outer', refs={'Actual': actual, 'Valuation': valuation,
        'Data': data, 'Scenarios': market, 'curves': curve_helpers})
    if route == 'collect':
        states.new_cells('state', 'lambda valuation_month, policy_id: Actual.collect().individual[policy_id].state[valuation_month]')
        outer.new_cells('actual_cashflows', 'lambda: Actual.collect().sum.net_cf')
        outer.new_cells('base_liability_pv', 'lambda y: Valuation.collect(y * 12, -1).sum.liability_pv')
        outer.new_cells('base_cashflows', 'lambda y: Valuation.collect(y * 12, -1).sum.net_cf')
        outer.new_cells('shocked_liability_pv', 'lambda y, key: Valuation.collect(y * 12, key).sum.liability_pv')
    else:
        states.new_cells('state', 'lambda valuation_month, policy_id: Actual[policy_id].policy_state(valuation_month)')
        outer.new_cells('actual_cashflows', """def actual_cashflows():
    result = {t: 0.0 for t in range(36)}
    for p in Actual.policy_ids:
        projection = Actual[p]
        for t in range(36):
            result[t] += projection.net_cf(t)
    return result""")
        outer.new_cells('base_liability_pv', """def base_liability_pv(y):
    total = 0.0
    for p in Valuation.policy_ids:
        total += Valuation(y * 12, p, -1).liability_pv()
    return total""")
        outer.new_cells('shocked_liability_pv', """def shocked_liability_pv(y, key):
    total = 0.0
    for p in Valuation.policy_ids:
        total += Valuation(y * 12, p, key).liability_pv()
    return total""")
        outer.new_cells('base_cashflows', """def base_cashflows(y):
    result = {t: 0.0 for t in range(480)}
    for p in Valuation.policy_ids:
        projection = Valuation(y * 12, p, -1)
        for t in range(480):
            result[t] += projection.net_cf(t)
    return result""")
    outer.new_cells('policy_state', 'lambda valuation_month, policy_id: Actual[policy_id].policy_state(valuation_month)' if route == 'direct' else 'lambda valuation_month, policy_id: Actual.collect().individual[policy_id].state[valuation_month]')
    outer.new_cells('dv01', 'lambda y, key: base_liability_pv(y) - shocked_liability_pv(y, key)')
    outer.new_cells('cs01', """def cs01(y, key):
    return base_liability_pv(y) - curves.rediscount_liability(
        base_cashflows(y).values(), Data.annual_curves[y], key_index=key)""")
    return model


def results(model):
    outer = model.Outer
    return {'base': np.array([outer.base_liability_pv(y) for y in range(3)]),
            'dv01': np.array([[outer.dv01(y, k) for k in range(7)] for y in range(3)]),
            'cs01': np.array([[outer.cs01(y, k) for k in range(7)] for y in range(3)]),
            'valuation_cf': np.array([list(outer.base_cashflows(y).values()) for y in range(3)]),
            'actual_cf': np.array(list(outer.actual_cashflows().values())),
            'annual_states': np.array([[outer.policy_state(m, p) for p in model.Actual.policy_ids]
                                       for m in VALUATION_MONTHS])}
