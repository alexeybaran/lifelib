"""Assemble canonical MYGA policy projections on stochastic G2++ market paths."""
from pathlib import Path
import math
import numpy as np
from . import actual, market, outer, outer_direct, valuation

KEY_MONTHS = (12, 24, 36, 60, 120, 180, 240)
OUTER_MONTHS = 36
HORIZON = 480
VALUATION_MONTHS = (0, 12, 24)


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
_TABLES = ('model_point_table', 'mort_table', 'withdrawal_table', 'surr_charge_table',
           'surr_charge_age_cap_table', 'mva_factor_table')


def _myga_data(model, source_path, folder, policy_table=None, linked=False):
    """The converted MYGA_US_S Data Space with the DV01 lookup Cells; optionally another policy table."""
    import modelx as mx

    source = mx.read_model(source_path, name=model.name + 'InputSource')
    try:
        data = source.Data.copy(model, 'Data')
        projection = source.Projection
        market_cells = ('scenario_id', 'scenario_table', 'scenario_rate')
        actual_formulas = {name: cell.formula.source for name, cell in projection.cells.items()
                           if name not in ('policy_id', *market_cells)}
        actual_refs = {name: getattr(projection, name) for name in projection.refs
                       if not name.startswith('__') and name not in ('data', 'point_id', 'RateColumn')}
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
    return data, actual_formulas, actual_refs


def _market_key(as_of_month, scen_id, shock=-1):
    if (isinstance(as_of_month, bool) or not isinstance(as_of_month, (int, np.integer))
            or not 0 <= as_of_month <= ESG.step_size()):
        raise ValueError('as_of_month is outside the generated ESG time grid')
    if (isinstance(scen_id, bool) or not isinstance(scen_id, (int, np.integer))
            or not 1 <= scen_id <= ESG.scen_size()):
        raise ValueError('scen_id must identify a generated ESG path')
    if (isinstance(shock, bool) or not isinstance(shock, (int, np.integer))
            or not -1 <= shock < len(key_months)):
        raise ValueError('shock must be -1 or a key-rate index')
    return None


def _actual_point(policy_id, scen_id):
    if (isinstance(scen_id, bool) or not isinstance(scen_id, (int, np.integer))
            or not 1 <= scen_id <= ESG.scen_size()):
        raise ValueError('scen_id must identify a generated ESG path')
    return {'refs': {'point_id': policy_id}}


def _valuation_point(valuation_month, policy_id, scen_id, shock=-1):
    if (isinstance(valuation_month, bool) or not isinstance(valuation_month, (int, np.integer))
            or not 0 <= valuation_month <= ESG.step_size()):
        raise ValueError('valuation_month is outside the generated ESG time grid')
    if (isinstance(scen_id, bool) or not isinstance(scen_id, (int, np.integer))
            or not 1 <= scen_id <= ESG.scen_size()):
        raise ValueError('scen_id must identify a generated ESG path')
    return {'refs': {'point_id': policy_id}}


def _copy_esg(model, esg_model, esg_input):
    import modelx as mx

    economic = Path(__file__).resolve().parents[4] / 'economic'
    source_path = Path(esg_model or economic / 'CashValue_ME_G2PP').resolve()
    source = mx.read_model(source_path, name=model.name + 'ESGSource')
    try:
        esg = source.ESG.copy(model, 'ESG')
    finally:
        source.close()
    esg.input_file = str(Path(esg_input or source_path.parent / esg.input_file).resolve())
    esg.param_table()
    esg.curve_knots()
    return esg


def _install_myga_formulas(actual_space, valuation_space, sources):
    for name in ('policy_ids', 'competitor_tenor', 'policy_state'):
        valuation_space.new_cells(name, actual_space.cells[name].formula.source)

    rollforwards = ('av_pp', 'mgsv_pp', 'interest_credited_pp', 'prem_accum_gmir_pp',
                    'free_wd_remain', 'tax_basis_pp', 'pols_if')
    for name, source in sources.items():
        if name not in actual_space.cells:
            actual_space.new_cells(name, source)
        if name not in valuation_space.cells:
            valuation_space.new_cells(name, source)
    for space in (actual_space, valuation_space):
        space.new_cells('contract_net_cf', sources['net_cf'])
    for name in rollforwards:
        valuation_space.new_cells(f'{name}_rollforward', sources[name])


def build_model(*, model_name='MYGAESGDV01', reference_dir=None,
                policy_table=None, route='collect', myga_model=None, esg_model=None, esg_input=None,
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
    model = mx.new_model(model_name)
    try:
        data, actual_formulas, actual_refs = _myga_data(model, myga_model, folder, policy_table, linked)
        ids = tuple(sorted(int(i) for i in data.model_point_table().index))
        if not ids or len(set(ids)) != len(ids):
            raise ValueError('policy IDs must be nonempty and unique')
        esg = _copy_esg(model, esg_model, esg_input)
        valuation_months = tuple(valuation_months)
        if (isinstance(outer_months, bool) or not isinstance(outer_months, (int, np.integer))
                or not 0 <= outer_months <= esg.step_size() + 1):
            raise ValueError('outer_months is outside the generated ESG time grid')
        if any(isinstance(month, bool) or not isinstance(month, (int, np.integer))
               or not 0 <= month <= esg.step_size() for month in valuation_months):
            raise ValueError('valuation months are outside the generated ESG time grid')
    except BaseException:
        model.close()
        raise
    market_space = model.new_space_from_module(market, name='Market', formula=_market_key,
        refs={'ESG': esg, 'key_months': KEY_MONTHS, 'shock_bp': 1.e-4, 'np': np})
    common = {**actual_refs, 'data': data, 'ESG': esg, 'Market': market_space, 'np': np, 'point_id': 0}
    actual_space = model.new_space_from_module(actual, name='Actual', formula=_actual_point,
        refs={**common, 'projection_months': tuple(range(outer_months)),
              'snapshot_months': valuation_months})
    valuation_space = model.new_space_from_module(valuation, name='Valuation', formula=_valuation_point,
        refs={**common, 'Actual': actual_space, 'HORIZON': HORIZON,
              'projection_months': tuple(range(HORIZON))})
    _install_myga_formulas(actual_space, valuation_space, actual_formulas)

    if route == 'collect':
        actual_space.set_collect(over={'policy_id': actual_space.policy_ids}, outputs=lambda: {
            'individual': {'state': {t: policy_state(t) for t in snapshot_months}},
            'sum': {'net_cf': {t: net_cf(t) for t in projection_months}}})
        valuation_space.set_collect(over={'policy_id': valuation_space.policy_ids}, outputs=lambda: {
            'sum': {'liability_pv': liability_pv(),
                    'net_cf': {k: cashflow_at_offset(k) for k in projection_months}}})

    outer_space = model.new_space_from_module(outer, name='Outer', refs={
        'Actual': actual_space, 'Valuation': valuation_space, 'ESG': esg,
        'Market': market_space, 'np': np})
    if route == 'direct':
        outer_space.new_cells_from_module(outer_direct)

    # Materialize the input table caches after assigning the references.
    for table in _TABLES:
        getattr(data, table)()
    return model


def results(model, scen_id):
    """Calculate the six portfolio reports for one generated ESG path."""
    outer = model.Outer
    months = model.Actual.snapshot_months
    keys = range(len(KEY_MONTHS))
    return {'base': np.array([outer.base_liability_pv(month, scen_id) for month in months]),
            'dv01': np.array([[outer.dv01(month, scen_id, k) for k in keys] for month in months]),
            'cs01': np.array([[outer.cs01(month, scen_id, k) for k in keys] for month in months]),
            'valuation_cf': np.array([list(outer.base_cashflows(month, scen_id).values()) for month in months]),
            'actual_cf': np.array(list(outer.actual_cashflows(scen_id).values())),
            'annual_states': np.array([[_policy_state(model, month, p, scen_id) for p in model.Actual.policy_ids()]
                                       for month in months])}


def _policy_state(model, valuation_month, policy_id, scen_id):
    """A policy's state at a valuation date: from the collected individual outputs (collect route) or
    from the policy's item (direct route)."""
    if 'collect_outputs' in model.Actual.cells:
        return model.Actual.collect(scen_id).individual[policy_id].state[valuation_month]
    return model.Actual[policy_id, scen_id].policy_state(valuation_month)
