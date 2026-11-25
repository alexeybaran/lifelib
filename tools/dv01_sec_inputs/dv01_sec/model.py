"""Assemble MYGA_US_SEC policy projections on the DV01 example's stochastic G2++ market paths.

Market, ESG and Outer are the DV01 example's own (lifelib uslib dv01 package, imported); Data is
MYGA_US_SEC's Data with the key-rate tenors and the book's projection end; Actual and Valuation
carry MYGA_US_SEC's Projection formulas, keyed by idx, with the market quotes of the example
(contract.py) and, for Valuation, the in-force restart (valuation.py).
"""
from pathlib import Path

import numpy as np
import pandas as pd

from lifelib.libraries.uslib.products.fixed_deferred_annuity.dv01 import market, outer
from lifelib.libraries.uslib.products.fixed_deferred_annuity.dv01.model import (
    OUTER_MONTHS, VALUATION_MONTHS, _copy_esg, _market_key, _shock_key_months)

from . import actual, contract, outer_direct, valuation

# MYGA_US_SEC cells the example replaces by market quotes: the deterministic rate scenario.
_DROPPED = ('scenario_rate', 'scenario_number', 'scenario_id')


def _book_projection_end():
    """Exclusive month end, from the valuation date, of the longest contract in the book."""
    months = 12 * (maturity_age - age_at_entry()) - duration_mth()
    return max(0, int(months.max()))


def _actual_point(idx, scen_id, through_month=-1):
    if (isinstance(scen_id, bool) or not isinstance(scen_id, (int, np.integer))
            or not 1 <= scen_id <= ESG.scen_size()):
        raise ValueError('scen_id must identify a generated ESG path')
    if (isinstance(through_month, bool) or not isinstance(through_month, (int, np.integer))
            or not -1 <= through_month < ESG.step_size()):
        raise ValueError('through_month is outside the generated ESG time grid')
    return None


def _valuation_point(valuation_month, idx, scen_id, shock=-1):
    if (isinstance(valuation_month, bool) or not isinstance(valuation_month, (int, np.integer))
            or not -1 <= valuation_month < ESG.step_size()):
        raise ValueError('valuation_month is outside the generated ESG time grid')
    if (isinstance(scen_id, bool) or not isinstance(scen_id, (int, np.integer))
            or not 1 <= scen_id <= ESG.scen_size()):
        raise ValueError('scen_id must identify a generated ESG path')
    if collect_history:
        if valuation_month == -1 or valuation_month in snapshot_months:
            history = Actual.collect(scen_id).individual[idx]
        else:
            history = Actual.collect(scen_id, valuation_month).individual[idx]
    else:
        history = Actual[idx, scen_id]
    return {'refs': {'act': history}}


def _sec_data(model, source_path):
    import modelx as mx

    source = mx.read_model(source_path, name=model.name + 'InputSource')
    try:
        data = source.Data.copy(model, 'Data')
        projection = source.Projection
        formulas = {name: cell.formula.source for name, cell in projection.cells.items()
                    if name not in _DROPPED}
        refs = {name: getattr(projection, name) for name in projection.refs
                if not name.startswith('__') and name not in ('data', 'idx')}
    finally:
        source.close()
    model.path = Path(source_path)
    data.maturity_age = refs['maturity_age']
    data.new_cells('shock_key_months', _shock_key_months)
    data.new_cells('book_projection_end', _book_projection_end)
    return data, formulas, refs


def _install(space, module_formulas, sec_formulas, renamed=()):
    """SEC formulas not already defined by the space's own module; net_cf kept as contract_net_cf."""
    for name, source in sec_formulas.items():
        if name not in space.cells:
            space.new_cells(name, source)
    space.new_cells('contract_net_cf', sec_formulas['net_cf'])


def build_model(*, model_name='MYGASECDV01', sec_model=None, route='collect', esg_model=None,
                esg_input=None, outer_months=OUTER_MONTHS, valuation_months=VALUATION_MONTHS):
    import modelx as mx
    if route not in ('collect', 'direct'):
        raise ValueError('route must be collect or direct')
    if sec_model is None:
        sec_model = Path(market.__file__).resolve().parents[1] / 'MYGA_US_SEC'
    model = mx.new_model(model_name)
    try:
        data, sec_formulas, sec_refs = _sec_data(model, sec_model)
        esg = _copy_esg(model, esg_model, esg_input)
        valuation_months = tuple(valuation_months)
    except BaseException:
        model.close()
        raise
    market_space = model.new_space_from_module(market, name='Market', formula=_market_key,
        refs={'ESG': esg, 'data': data, 'shock_bp': 1.e-4, 'np': np})
    market_space.absref(Market=market_space)
    common = {**sec_refs, 'data': data, 'ESG': esg, 'Market': market_space, 'np': np}
    last = max(valuation_months, default=-1)
    actual_space = model.new_space_from_module(actual, name='Actual', formula=_actual_point,
        refs={**common, 'projection_months': tuple(range(outer_months)),
              'snapshot_months': valuation_months, 'last_snapshot_month': last})
    valuation_space = model.new_space_from_module(valuation, name='Valuation', formula=_valuation_point,
        refs={**common, 'Actual': actual_space, 'act': None, 'collect_history': route == 'collect',
              'snapshot_months': valuation_months, 'last_snapshot_month': last})
    for space in (actual_space, valuation_space):
        space.new_cells_from_module(contract)
    valuation_space.new_cells('point_indices', actual_space.cells['point_indices'].formula.source)
    _install(actual_space, actual, sec_formulas)
    _install(valuation_space, valuation, sec_formulas)

    if route == 'collect':
        actual_space.set_collect(over={'idx': actual_space.point_indices}, outputs=lambda: {
            'individual': {
                'pols_if_open': {t: pols_if_open(t) for t in open_months()},
                'av_pp_open': {t: av_pp_open(t) for t in open_months()},
                'mgsv_pp_open': {t: mgsv_pp_open(t) for t in open_months()},
                'prem_accum_gmir_pp_open': {t: prem_accum_gmir_pp_open(t) for t in open_months()},
                'interest_credited_pp_open': {t: interest_credited_pp_open(t) for t in open_months()},
                'interest_credited_pp_prev_anniv_open': {
                    t: interest_credited_pp_prev_anniv_open(t) for t in open_months()},
                'free_wd_allow_open': {t: free_wd_allow_open(t) for t in open_months()},
                'free_wd_remain_open': {t: free_wd_remain_open(t) for t in open_months()},
                'tax_basis_pp_open': {t: tax_basis_pp_open(t) for t in open_months()},
                'credit_rate_open': {t: credit_rate_open(t) for t in open_months()},
                'mva_ref_yield_locked_open': {t: mva_ref_yield_locked_open(t) for t in open_months()},
            },
            'sum': {'net_cf': {t: net_cf(t) for t in projection_months}}})
        valuation_space.set_collect(over={'idx': valuation_space.point_indices}, outputs=lambda: {
            'sum': {'liability_pv': liability_pv(),
                    'net_cf': {k: cashflow_at_offset(k) for k in projection_months(valuation_month)}}})

    outer_space = model.new_space_from_module(outer, name='Outer', refs={
        'Actual': actual_space, 'Valuation': valuation_space, 'ESG': esg,
        'Market': market_space, 'data': data, 'pd': pd, 'np': np})
    if route == 'direct':
        outer_space.new_cells_from_module(outer_direct)
    for table in ('model_point_table', 'mort_table', 'surr_charge_table', 'surr_charge_age_cap_table',
                  'rate_scenario', 'withdrawal_table', 'mva_factor_table'):
        getattr(data, table)()
    return model
