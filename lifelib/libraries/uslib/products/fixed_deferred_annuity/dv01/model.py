"""DV01 with shared raw data and scenario Cells, for live/export/Cython.

The retained example's Actual/Valuation economic conventions remain unchanged.
No policy-month arrays are prepared before the formula graph executes.
"""
from pathlib import Path
import inspect
import math
import numpy as np
import pandas as pd
from . import policy, assumptions, scenario, curve_helpers, curves as curve_formulas

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


# The DV01 lookup Cells read the converted MYGA_US_S Data tables directly, as the MYGA Projection
# reads them (``.loc`` by key; a missing withdrawal or surrender key is zero; the MVA factor is
# interpolated between whole years and held beyond the last row). No lookup helper module.
_DATA_CELLS = {
    'numeric_field': "lambda policy_id, column: float(model_point_table().loc[policy_id, column])",
    'label_field': "lambda policy_id, column: str(model_point_table().loc[policy_id, column])",
    'mortality_rate': "lambda age, sex: float(mort_table().loc[(age, Sex[sex]), 'mort_rate'])",
    'withdrawal_amount': '''def withdrawal_amount(schedule, month):
    table = withdrawal_table()
    key = (schedule, month)
    return float(table.loc[key, 'wd_amount']) if key in table.index else 0.0
''',
    'surrender_rate': '''def surrender_rate(schedule, year):
    table = surr_charge_table()
    key = (Schedule[schedule], year)
    return float(table.loc[key, 'surr_charge_rate']) if key in table.index else 0.0
''',
    'mva_factor': '''def mva_factor(term, column):
    table = mva_factor_table()
    name = 'factor_hi' if column else 'factor_lo'
    last = int(table.index.max())
    lower = int(math.floor(term))
    if lower >= last:
        return float(table.loc[last, name])
    f0 = float(table.loc[lower, name])
    f1 = float(table.loc[lower + 1, name])
    return f0 + (f1 - f0) * (term - lower)
''',
    'mva_factor_lo': 'lambda term: mva_factor(term, 0)',
    'mva_factor_hi': 'lambda term: mva_factor(term, 1)',
}
# Unlinked builds hold the policy table as a reference and read it directly (live invalidation by reference).
_POLICY_REF_CELLS = {
    'numeric_field': "lambda policy_id, column: float(policy_table.loc[policy_id, column])",
    'label_field': "lambda policy_id, column: str(policy_table.loc[policy_id, column])",
}
_TABLES = ('model_point_table', 'mort_table', 'withdrawal_table', 'surr_charge_table', 'mva_factor_table')


def _myga_data(model, source_path, folder, policy_table=None, linked=False):
    """The converted MYGA_US_S Data Space with the DV01 lookup Cells; optionally another policy table."""
    import modelx as mx

    source = mx.read_model(source_path, name=model.name + 'InputSource')
    try:
        data = source.Data.copy(model, 'Data')
    finally:
        source.close()
    model.path = folder / Path(source_path).name
    data.math = math
    cells = dict(_DATA_CELLS)
    if not linked:
        # The policy table is a reference read once (or supplied); replacing it changes the policies.
        data.policy_table = (data.model_point_table() if policy_table is None else policy_table)
        data.model_point_table.formula = lambda: policy_table
        cells.update(_POLICY_REF_CELLS)
    for name, formula in cells.items():
        data.new_cells(name, formula)
    return data


def build_model(*, model_name='MYGASharedDataDV01', reference_dir=None,
                policy_table=None, route='collect', myga_model=None):
    import modelx as mx
    if route not in ('collect', 'direct'):
        raise ValueError('route must be collect or direct')
    if myga_model is not None and policy_table is not None:
        raise ValueError('use the saved MYGA Data Cell or supply policy_table')
    linked = myga_model is not None
    folder = Path(reference_dir or (Path(myga_model).parent if myga_model is not None
                                   else Path(__file__).resolve().parent.parent))
    myga_model = myga_model or folder / 'MYGA_US_S'
    if policy_table is not None:
        policy_table = policy_table.sort_index()
        if not policy_table.index.is_unique or len(policy_table) == 0:
            raise ValueError('policy IDs must be nonempty and unique')
    curves, spreads = curve_helpers.outer_scenario()
    model = mx.new_model(model_name)
    try:
        data = _myga_data(model, myga_model, folder, policy_table, linked)
        data.annual_curves = curves
        data.annual_spreads = spreads
        data.curves = curve_helpers
        ids = tuple(sorted(int(i) for i in data.model_point_table().index))
        if not ids or len(set(ids)) != len(ids):
            raise ValueError('policy IDs must be nonempty and unique')
    except BaseException:
        model.close()
        raise
    curve_space = model.new_space('Curves', refs={
        'Data': data, 'helpers': curve_helpers, 'np': np,
        'tenors': curve_helpers.KRD_TENORS, 'shock_bp': curve_helpers.KRD_BP,
        'outer_months': OUTER_MONTHS, 'valuation_horizon': HORIZON})
    for name, formula in inspect.getmembers(curve_formulas, inspect.isfunction):
        curve_space.new_cells(name, formula)
    data.Curves = curve_space
    data.new_cells('monthly_inputs', 'lambda: Curves.monthly_inputs()')
    data.new_cells('monthly_curves', 'lambda: Curves.monthly_curves()')
    data.new_cells('monthly_spreads', 'lambda: Curves.monthly_spreads()')
    market = model.new_space('Scenarios',
        formula=lambda valuation_month=0, forward_project=False, shock=-1: None,
        refs={'Data': data, 'curves': curve_helpers, 'Curves': curve_space})
    for name, formula in inspect.getmembers(scenario, inspect.isfunction):
        market.new_cells(name, formula)
    initial = model.new_space('Initial', formula=lambda policy_id: None,
        refs={'Data': data, 'Scenarios': market, 'np': np})
    initial.new_cells('state', initial_state)
    states = model.new_space('StateSource')
    common = {'policy_ids': ids, 'np': np, 'Data': data,
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
        'Data': data, 'Scenarios': market, 'curves': curve_helpers,
        'Curves': curve_space, 'np': np})
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
    # The run's input snapshot: every input table is read once here, after the last reference
    # assignment; no file is read during the calculation.
    for table in _TABLES:
        getattr(data, table)()
    outer.new_cells('cs01', """def cs01(y, key):
    cashflows = np.asarray(tuple(base_cashflows(y).values()), dtype=np.float64)
    liability = float(-np.dot(cashflows, Curves.discount_factors(y, key)))
    return base_liability_pv(y) - liability""")
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
