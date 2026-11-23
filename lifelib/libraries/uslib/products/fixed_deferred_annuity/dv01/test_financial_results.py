"""Reconcile the six pathwise reports to policy cash flows and raw G2++ prices."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from .model import build_model, results
from .test_market import expected_price


@pytest.fixture
def policy_table():
    folder = Path(__file__).resolve().parents[1]
    table = pd.read_csv(folder / 'model_point_table.csv', index_col='point_id').loc[[1, 3]].copy()
    table['age_at_entry'] = [98, 99]
    table['guar_period'] = [1, 1]
    return table


def expected_reports(model, ids, scenario):
    months = model.Actual.snapshot_months
    engine = model.ESG
    projections = [model.Actual(policy, scenario) for policy in ids]
    end = max(projection.proj_len() for projection in projections)
    horizon = max((max(0, end - month - 1) for month in months), default=0)
    actual_cf = [sum(projection.net_cf(t) for projection in projections)
                 for t in model.Actual.projection_months]
    states = []
    for month in months:
        previous = month - 1
        year_start = month // 12 * 12
        rows = []
        for projection in projections:
            interest = projection.interest_credited_pp(previous) if month else 0.0
            prior_year_interest = projection.interest_credited_pp(year_start - 1) if year_start else 0.0
            rows.append([
                projection.av_pp_at(month, projection.AvTiming.BEF_WD),
                projection.mgsv_pp(previous) if month else projection.mgsv_pp_init(),
                projection.pols_if(month),
                interest,
                interest - prior_year_interest,
                projection.prem_accum_gmir_pp(previous) if month else projection.premium_pp(),
                projection.free_wd_avail(month),
                projection.credit_rate(month),
                projection.mva_ref_yield_locked(month),
            ])
        states.append(rows)
    base_liabilities, base_cashflows, dv01, cs01 = [], [], [], []
    for month in months:
        first_projected = month + 1
        projected_months = range(first_projected, end)
        cashflows_by_shock, base_discounts_by_shock = [], []
        for shock in [-1, *range(len(model.Data.shock_key_months()))]:
            items = [model.Valuation(month, policy, scenario, shock) for policy in ids]
            cashflows = [sum(item.net_cf(t) for item in items) for t in projected_months]
            discounts = [expected_price(engine, first_projected, t + 1, scenario, shock)
                         for t in projected_months]
            if shock == -1:
                base_flows = cashflows
                base_pv = -np.dot(base_flows, discounts)
                base_liabilities.append(base_pv)
                base_cashflows.append(np.pad(base_flows, (0, horizon - len(base_flows))))
            else:
                cashflows_by_shock.append(base_pv + np.dot(cashflows, discounts))
                base_discounts_by_shock.append(base_pv + np.dot(base_flows, discounts))
        dv01.append(cashflows_by_shock)
        cs01.append(base_discounts_by_shock)
    return {'base': base_liabilities, 'dv01': dv01, 'cs01': cs01,
            'valuation_cf': base_cashflows, 'actual_cf': actual_cf, 'annual_states': states}


@pytest.mark.parametrize('route', ['direct', 'collect'])
def test_all_reports_reconcile_independently_for_each_esg_path(route, policy_table):
    model = build_model(route=route, policy_table=policy_table, outer_months=24,
                        valuation_months=(0, 3, 12))
    try:
        flow_paths = []
        for scenario in (1, 2):
            observed = results(model, scenario)
            expected = expected_reports(model, policy_table.index, scenario)
            assert set(observed) == set(expected)
            for name, values in observed.items():
                assert values.shape == np.shape(expected[name]), name
                if name == 'annual_states':
                    np.testing.assert_array_equal(values, expected[name], err_msg=name)
                else:
                    np.testing.assert_allclose(values, expected[name], rtol=1e-10, atol=1e-7, err_msg=name)
            flow_paths.append(observed['actual_cf'])
        assert not np.array_equal(*flow_paths)
    finally:
        model.close()


@pytest.mark.parametrize('route', ['direct', 'collect'])
def test_maturity_at_cut_stays_in_actual_cashflows(route, policy_table):
    table = policy_table.loc[[3]]
    cut = 11
    model = build_model(route=route, policy_table=table, outer_months=13,
                        valuation_months=(cut,))
    try:
        actual = model.Actual(3, 2)
        ended = model.Valuation(cut, 3, 2, -1)
        assert ended.proj_len() == 12
        assert ended.net_cf(cut) == actual.net_cf(cut) < 0.0
        assert model.Outer.actual_cashflows(2)[cut] == actual.net_cf(cut)
        assert ended.net_cf(12) == 0.0
        assert model.Outer.base_cashflows(cut, 2) == {}
        for offset in (-1, 0, 479, 480):
            assert ended.cashflow_at_offset(offset) == 0.0
        assert ended.pols_if(12) == 0.0
        assert ended.liability_pv() == 0.0
        assert model.Outer.base_liability_pv(cut, 2) == 0.0
        assert model.Valuation(24, 3, 2, -1).liability_pv() == 0.0
    finally:
        model.close()


def test_book_horizon_can_extend_beyond_the_old_limit(policy_table):
    table = policy_table.copy()
    table.at[1, 'age_at_entry'] = 55
    model = build_model(route='direct', policy_table=table)
    try:
        assert model.Data.book_projection_end() == 540
        assert model.Valuation(12, 1, 1, -1).remaining_months() == 527
        assert model.Valuation(12, 3, 1, -1).remaining_months() == 0
        assert tuple(model.Valuation.projection_months(12)) == tuple(range(527))
    finally:
        model.close()
