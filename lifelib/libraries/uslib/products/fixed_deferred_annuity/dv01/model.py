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
from lifelib.libraries.uslib.products.fixed_deferred_annuity import enums   # the MYGA_US_S enums

OUTER_MONTHS = 36
HORIZON = 480
VALUATION_MONTHS = (0, 12, 24)


def actual_initial_state():
    """The state at issue: account value, MGSV, policies in force, interest to date, interest this
    year, premium accumulated at the GMIR, free withdrawal available, credited rate, locked MVA rate."""
    premium = premium_pp()
    rate = max(gmir(), market().rate(0, 5.0) - market().spread(0))
    free = free_rate() * premium if free_rule() == 0.0 else 0.0
    return (premium, 0.875 * premium, pols_if_init(), 0.0, 0.0, premium, free, rate, market().rate(0, 5.0))


# The DV01 lookup Cells read the converted MYGA_US_S Data tables directly, as the MYGA Projection
# reads them (``.loc`` by key; a missing withdrawal or surrender key is zero; the MVA factor is
# interpolated between whole years and held beyond the last row). No lookup helper module.
_DATA_CELLS = {
    'mortality_rate': "lambda age, sex: float(mort_table().loc[(age, sex), 'mort_rate'])",
    'surrender_rate': '''def surrender_rate(schedule, year):
    table = surr_charge_table()
    key = (schedule, year)
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
    for name, formula in cells.items():
        data.new_cells(name, formula)
    return data


def build_model(*, model_name='MYGASharedDataDV01', reference_dir=None,
                policy_table=None, route='collect', myga_model=None,
                outer_months=OUTER_MONTHS, valuation_months=VALUATION_MONTHS):
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
        'outer_months': outer_months, 'valuation_horizon': HORIZON})
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
    # The policy is the item of Actual and Valuation (their parameter policy_id); no Cell takes a
    # policy as an argument, so nothing is sized by the book.
    # The book is read by a Cell, policy_ids(), of each collected Space: another model point table
    # is another book, with nothing else to change.
    # Closed-set labels are the MYGA_US_S enums (IntEnum), as its Projection uses them.
    common = {'Data': data, 'Scenarios': market, 'mva_admin_spread': 0.0025,
              'Sex': enums.Sex, 'Renewal': enums.Renewal, 'Schedule': enums.Schedule}
    actual = model.new_space('Actual', formula=lambda policy_id: None,
        refs={**common, 'valuation_month': 0, 'HORIZON': outer_months,
              'projection_months': tuple(range(outer_months)), 'snapshot_months': tuple(valuation_months)})
    valuation = model.new_space('Valuation', formula=lambda valuation_month, policy_id, shock=-1: None,
        refs={**common, 'Actual': actual, 'HORIZON': HORIZON,
              'projection_months': tuple(range(HORIZON))})
    for space in (actual, valuation):
        space.new_cells('policy_ids', 'lambda: tuple(sorted(int(p) for p in Data.model_point_table().index))')
    actual.new_cells('market', 'lambda: Scenarios(0, False, -1)')
    actual.new_cells('initial_state', actual_initial_state)
    valuation.new_cells('market', 'lambda: Scenarios(valuation_month, True, shock)')
    valuation.new_cells('initial_state', (
        'lambda: Actual.collect().individual[policy_id].state[valuation_month]' if route == 'collect' else
        'lambda: Actual[policy_id].policy_state(valuation_month)'))
    if route == 'collect':
        actual.set_collect(over={'policy_id': actual.policy_ids}, outputs=lambda: {
            'individual': {'state': {t: policy_state(t) for t in snapshot_months}},
            'sum': {'net_cf': {t: net_cf(t) for t in projection_months}}})
        valuation.set_collect(over={'policy_id': valuation.policy_ids}, outputs=lambda: {
            'sum': {'liability_pv': liability_pv(),
                    'net_cf': {t: net_cf(t) for t in projection_months}}})
    for space in (actual, valuation):
        for module in (policy, assumptions):
            for name, formula in inspect.getmembers(module, inspect.isfunction):
                if name in space.cells:
                    space.cells[name].formula = formula
                else:
                    space.new_cells(name, formula)
        # the policy's model point, one row of the policy table, and its fields
        space.new_cells('model_point', 'lambda: Data.model_point_table().loc[policy_id]')
        fields = {'premium_pp': 'premium', 'gmir': 'gmir', 'mgsv_rate': 'mgsv_rate',
                  'mgsv_charge': 'mgsv_annual_charge', 'free_rate': 'free_wd_rate',
                  'premium_tax': 'premium_tax_rate',
                  'pols_if_init': 'pols_if_init', 'free_exempt': 'free_wd_mva_exempt'}
        for name, column in fields.items():
            space.new_cells(name, f"lambda: float(model_point()[{column!r}])")
        space.new_cells('age_at_entry', "lambda: int(model_point()['age_at_entry'])")   # an integer, as in MYGA_US_S
        space.new_cells('sex', "lambda: Sex[model_point()['sex']]")
        space.new_cells('renewal_architecture', "lambda: Renewal[model_point()['renewal_architecture']]")
        space.new_cells('wd_schedule_id', "lambda: str(model_point()['wd_schedule_id'])")
        # the policy's withdrawal programme, read by month (as the MYGA_US_S Projection reads it)
        space.new_cells('has_withdrawals', "lambda: wd_schedule_id() in Data.withdrawal_table().index")
        space.new_cells('withdrawal_rows', "lambda: Data.withdrawal_table().loc[wd_schedule_id()]")
        space.new_cells('mgsv_net_wd', "lambda: 1.0 if model_point()['mgsv_wd_convention'] == 'net_of_charges' else 0.0")
        space.new_cells('free_rule', "lambda: 0.0 if model_point()['free_wd_rule'] == 'pct_av' else 1.0")
        space.new_cells('mva_family', """def mva_family():
    name = model_point()['mva_family']
    return {'linear_duration': 0.0, 'geometric': 1.0, 'declared_differential': 2.0}[name]""")
        space.new_cells('mva_cap', """def mva_cap():
    name = model_point()['mva_cap_rule']
    return {'sym_sc': 0.0, 'min_sc_interest': 1.0, 'asym_sc_snfl': 2.0, 'gmir_floor': 3.0, 'none': 4.0}[name]""")
    outer = model.new_space('Outer', refs={'Actual': actual, 'Valuation': valuation,
        'Data': data, 'Scenarios': market, 'curves': curve_helpers,
        'Curves': curve_space, 'np': np})
    if route == 'collect':
        outer.new_cells('actual_cashflows', 'lambda: Actual.collect().sum.net_cf')
        outer.new_cells('base_liability_pv', 'lambda y: Valuation.collect(y * 12, -1).sum.liability_pv')
        outer.new_cells('base_cashflows', 'lambda y: Valuation.collect(y * 12, -1).sum.net_cf')
        outer.new_cells('shocked_liability_pv', 'lambda y, key: Valuation.collect(y * 12, key).sum.liability_pv')
    else:
        outer.new_cells('actual_cashflows', """def actual_cashflows():
    result = {t: 0.0 for t in Actual.projection_months}
    for p in Actual.policy_ids():
        projection = Actual[p]
        for t in Actual.projection_months:
            result[t] += projection.net_cf(t)
    return result""")
        outer.new_cells('base_liability_pv', """def base_liability_pv(y):
    total = 0.0
    for p in Valuation.policy_ids():
        total += Valuation(y * 12, p, -1).liability_pv()
    return total""")
        outer.new_cells('shocked_liability_pv', """def shocked_liability_pv(y, key):
    total = 0.0
    for p in Valuation.policy_ids():
        total += Valuation(y * 12, p, key).liability_pv()
    return total""")
        outer.new_cells('base_cashflows', """def base_cashflows(y):
    result = {t: 0.0 for t in range(480)}
    for p in Valuation.policy_ids():
        projection = Valuation(y * 12, p, -1)
        for t in range(480):
            result[t] += projection.net_cf(t)
    return result""")
    outer.new_cells('dv01', 'lambda y, key: base_liability_pv(y) - shocked_liability_pv(y, key)')
    # by valuation month (any month of the Actual projection): the liability PV, base (key -1) or shocked
    outer.new_cells('liability_pv', 'lambda month, key: Valuation.collect(month, key).sum.liability_pv'
                    if route == 'collect' else '''def liability_pv(month, key):
    total = 0.0
    for p in Valuation.policy_ids():
        total += Valuation(month, p, key).liability_pv()
    return total''')
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
            'annual_states': np.array([[_policy_state(model, m, p) for p in model.Actual.policy_ids()]
                                       for m in VALUATION_MONTHS])}


def _policy_state(model, valuation_month, policy_id):
    """A policy's state at a valuation date: from the collected individual outputs (collect route) or
    from the policy's item (direct route)."""
    if 'collect_outputs' in model.Actual.cells:
        return model.Actual.collect().individual[policy_id].state[valuation_month]
    return model.Actual[policy_id].policy_state(valuation_month)
