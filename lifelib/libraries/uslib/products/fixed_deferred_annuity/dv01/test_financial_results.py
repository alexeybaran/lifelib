"""Validate the flattened valuation against the recorded nested MYGA results."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lifelib.libraries.uslib.products.fixed_deferred_annuity.dv01 import model as dv01


ORACLE_PATH = Path(__file__).with_name('test_financial_results_5410014.json')


@pytest.fixture
def policy_table():
    model_points = Path(__file__).resolve().parent.parent / 'model_point_table.csv'
    table = pd.read_csv(model_points, index_col='point_id').loc[[1, 3, 5]].copy()
    # Keep the renewal and withdrawal rules while shortening the projections.
    table['age_at_entry'] = [96, 99, 97]
    table['guar_period'] = [1, 1, 2]
    return table


def finance_model(route, table):
    model = dv01.build_model(route=route, policy_table=table, model_name='FinancialResults')
    # A slope makes the restart-relative forward offset observable across tenors.
    model.Data.annual_curves = model.Data.annual_curves + np.arange(7) * 0.001
    return model


@pytest.mark.parametrize('route', ['direct', 'collect'])
def test_all_financial_outputs_match_nested_model(route, policy_table):
    # The fixture was generated with this same book and curves on commit 5410014.
    oracle = json.loads(ORACLE_PATH.read_text(encoding='utf-8'))
    model = finance_model(route, policy_table)
    try:
        results = dv01.results(model)
    finally:
        model.close()

    assert set(results) == set(oracle)
    for name, observed in results.items():
        expected = np.asarray(oracle[name])
        if name == 'valuation_cf':
            # Each recorded row has a common 48-month prefix. All later months are zero.
            assert observed.shape == (3, 480)
            np.testing.assert_array_equal(observed[:, expected.shape[1]:], 0.0)
            observed = observed[:, :expected.shape[1]]
        assert observed.shape == expected.shape, name
        magnitude = np.abs(expected)
        if name in ('dv01', 'cs01'):
            base = np.asarray(oracle['base'])[:, None]
            magnitude = np.abs(base) + np.abs(base - expected)
        np.testing.assert_array_less(np.abs(observed - expected), 1e-7 + 1e-10 * magnitude,
                                     err_msg=name)


def test_expired_policy_cashflows(policy_table):
    model = finance_model('direct', policy_table)
    try:
        ended = model.Valuation(12, 3, -1)
        assert ended.proj_len() == 12
        assert ended.net_cf(11) == model.Actual[3].net_cf(11) < 0.0
        assert ended.net_cf(12) == 0.0
        assert ended.cashflow_at_offset(-1) == 0.0
        assert ended.cashflow_at_offset(0) == 0.0
        assert ended.cashflow_at_offset(479) == 0.0
        assert ended.cashflow_at_offset(480) == 0.0
        assert ended.state_at_offset(0)[2] == 0.0
        assert ended.liability_pv() == 0.0
        assert model.Valuation(24, 3, -1).liability_pv() == 0.0
    finally:
        model.close()
