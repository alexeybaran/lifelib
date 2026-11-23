"""Assemble canonical MYGA policy projections on stochastic G2++ market paths."""
from pathlib import Path
import math
import pathlib
import lifelib
import numpy as np
from . import actual, market, outer, outer_direct, valuation


OUTER_MONTHS = 36
VALUATION_MONTHS = (0, 12, 24)

# Column order of the annual financial report.
OPENING_COLUMNS = (
    'opening_account_value',
    'opening_guaranteed_surrender_value',
    'pols_if',
    'interest_credited_to_date',
    'interest_credited_policy_year_to_date',
    'opening_accumulated_guaranteed_premiums',
    'free_wd_avail',
    'credit_rate',
    'mva_ref_yield_locked',
)


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


def _shock_key_months():
    """Ordered key tenors in whole months, read once from the book's input directory."""
    table = pd.read_csv(input_dir() / 'shock_steps.csv')
    if list(table.columns) != ['tenor_months'] or table.empty:
        raise ValueError('shock_steps.csv requires one tenor_months column and at least one row')
    values = table['tenor_months']
    if (not pd.api.types.is_integer_dtype(values.dtype) or values.min() <= 0
            or not values.is_monotonic_increasing or not values.is_unique):
        raise ValueError('shock tenors must be positive whole months in strictly increasing order')
    return values.tolist()


def _book_projection_end():
    """Exclusive policy-month end for the longest MYGA contract in the book."""
    age = min(int(value) for value in model_point_table()['age_at_entry'])
    return max(0, 12 * (maturity_age - age))


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
    data.maturity_age = actual_refs['maturity_age']
    data.new_cells('shock_key_months', _shock_key_months)
    data.new_cells('book_projection_end', _book_projection_end)
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
            or not -1 <= shock < len(data.shock_key_months())):
        raise ValueError('shock must be -1 or a key-rate index')
    return None


def _actual_point(policy_id, scen_id, through_month=-1):
    if (isinstance(scen_id, bool) or not isinstance(scen_id, (int, np.integer))
            or not 1 <= scen_id <= ESG.scen_size()):
        raise ValueError('scen_id must identify a generated ESG path')
    if (isinstance(through_month, bool) or not isinstance(through_month, (int, np.integer))
            or not -1 <= through_month < ESG.step_size()):
        raise ValueError('through_month is outside the generated ESG time grid')
    return {'refs': {'point_id': policy_id}}


def _valuation_point(valuation_month, policy_id, scen_id, shock=-1):
    if (isinstance(valuation_month, bool) or not isinstance(valuation_month, (int, np.integer))
            or not 0 <= valuation_month < ESG.step_size()):
        raise ValueError('valuation_month is outside the generated ESG time grid')
    if (isinstance(scen_id, bool) or not isinstance(scen_id, (int, np.integer))
            or not 1 <= scen_id <= ESG.scen_size()):
        raise ValueError('scen_id must identify a generated ESG path')
    if collect_history:
        if valuation_month <= last_snapshot_month:
            history = Actual.collect(scen_id).individual[policy_id]
        else:
            history = Actual.collect(scen_id, valuation_month).individual[policy_id]
    else:
        history = Actual[policy_id, scen_id]
    return {'refs': {'point_id': policy_id, 'act': history}}


def _packaged_input_path():
    return pathlib.Path(lifelib.__file__).parent / 'libraries' / 'economic' / input_file


def _copy_esg(model, esg_model, esg_input):
    import modelx as mx

    economic = Path(__file__).resolve().parents[4] / 'economic'
    source_path = Path(esg_model or economic / 'CashValue_ME_G2PP').resolve()
    source = mx.read_model(source_path, name=model.name + 'ESGSource')
    try:
        esg = source.ESG.copy(model, 'ESG')
    finally:
        source.close()
    if 'P_t_T_path' not in esg.cells:
        esg.new_cells('P_t_T_path', 'lambda i, j, scen_id: float(P_t_T(i, j)[scen_id - 1])')
    if esg_model is None:
        esg.lifelib = lifelib
        esg.pathlib = pathlib
        esg.input_path.formula = _packaged_input_path
    if esg_input is not None:
        esg.input_file = str(Path(esg_input).resolve())
    elif esg_model is not None:
        esg.input_file = str((source_path.parent / esg.input_file).resolve())
    esg.param_table()
    esg.curve_knots()
    return esg


def _install_myga_formulas(actual_space, valuation_space, sources):
    for name in ('policy_ids', 'competitor_tenor', *OPENING_COLUMNS):
        if name in valuation_space.cells or name not in actual_space.cells:
            continue
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
               or not 0 <= month < esg.step_size() for month in valuation_months):
            raise ValueError('valuation months are outside the generated ESG time grid')
    except BaseException:
        model.close()
        raise
    market_space = model.new_space_from_module(market, name='Market', formula=_market_key,
        refs={'ESG': esg, 'data': data, 'shock_bp': 1.e-4, 'np': np})
    market_space.absref(Market=market_space)
    common = {**actual_refs, 'data': data, 'ESG': esg, 'Market': market_space, 'np': np, 'point_id': 0}
    actual_space = model.new_space_from_module(actual, name='Actual', formula=_actual_point,
        refs={**common, 'projection_months': tuple(range(outer_months)),
              'snapshot_months': valuation_months, 'last_snapshot_month': max(valuation_months, default=-1)})
    valuation_space = model.new_space_from_module(valuation, name='Valuation', formula=_valuation_point,
        refs={**common, 'Actual': actual_space,
              'act': None, 'collect_history': route == 'collect',
              'last_snapshot_month': max(valuation_months, default=-1)})
    _install_myga_formulas(actual_space, valuation_space, actual_formulas)

    if route == 'collect':
        actual_space.set_collect(over={'policy_id': actual_space.policy_ids}, outputs=lambda: {
            'individual': {
                'av_pp': {t: av_pp(t) for t in history_months()},
                'mgsv_pp': {t: mgsv_pp(t) for t in history_months()},
                'interest_credited_pp': {t: interest_credited_pp(t) for t in history_months()},
                'prem_accum_gmir_pp': {t: prem_accum_gmir_pp(t) for t in history_months()},
                'opening_account_value': {t: opening_account_value(t) for t in snapshot_months},
                'opening_guaranteed_surrender_value': {t: opening_guaranteed_surrender_value(t) for t in snapshot_months},
                'pols_if': {t: pols_if(t) for t in opening_months()},
                'interest_credited_to_date': {t: interest_credited_to_date(t) for t in snapshot_months},
                'interest_credited_policy_year_to_date': {t: interest_credited_policy_year_to_date(t) for t in snapshot_months},
                'opening_accumulated_guaranteed_premiums': {t: opening_accumulated_guaranteed_premiums(t) for t in snapshot_months},
                'free_wd_avail': {t: free_wd_avail(t) for t in snapshot_months},
                'credit_rate': {t: credit_rate(t) for t in history_months()},
                'mva_ref_yield_locked': {t: mva_ref_yield_locked(t) for t in history_months()},
                'free_wd_remain': {t: free_wd_remain(t) for t in history_months()},
                'tax_basis_pp': {t: tax_basis_pp(t) for t in history_months()},
                'net_cf': {t: net_cf(t) for t in history_months()},
            },
            'sum': {'net_cf': {t: net_cf(t) for t in projection_months}}})
        valuation_space.set_collect(over={'policy_id': valuation_space.policy_ids}, outputs=lambda: {
            'sum': {'liability_pv': liability_pv(),
                    'net_cf': {k: cashflow_at_offset(k) for k in projection_months(valuation_month)}}})

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
    keys = range(len(model.Data.shock_key_months()))
    base = np.array([outer.base_liability_pv(month, scen_id) for month in months])
    cashflows = [outer.base_cashflows(month, scen_id) for month in months]
    width = max(map(len, cashflows), default=0)
    aligned = np.zeros((len(months), width))
    for row, values in zip(aligned, cashflows):
        row[:len(values)] = [values[k] for k in range(len(values))]
    return {'base': base,
            'dv01': np.array([[outer.dv01(month, scen_id, k) for k in keys] for month in months]),
            'cs01': np.array([[outer.cs01(month, scen_id, k) for k in keys] for month in months]),
            'valuation_cf': aligned,
            'actual_cf': np.array(list(outer.actual_cashflows(scen_id).values())),
            'annual_states': _annual_openings(model.Actual, scen_id, months)}


def _annual_openings(actual, scen_id, months):
    policies = actual.policy_ids()
    if hasattr(actual, 'collect_outputs'):
        records = actual.collect(scen_id).individual
        return np.array([[[getattr(records[p], name)[t] for name in OPENING_COLUMNS]
                          for p in policies] for t in months])
    return np.array([[[getattr(actual[p, scen_id], name)(t) for name in OPENING_COLUMNS]
                      for p in policies] for t in months])
