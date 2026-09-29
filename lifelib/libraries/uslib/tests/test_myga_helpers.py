"""The MYGA helper interface in live modelx and exported Python."""
import importlib
import sys

import modelx as mx
import numpy as np
import pandas as pd
import pytest

from lifelib.helpers.lookups import power
from us_registry import LIB
from lifelib.libraries.uslib.myga_enums import AccountTiming, Claim, Sex


MODEL = LIB / 'products/fixed_deferred_annuity/MYGA_US_S'


def test_real_power_intrinsic_declaration_preserves_errors():
    assert power.__modelx_cython_intrinsic__ == 'real_power_v1'
    assert power(-2.0, 3.0) == -8.0
    assert power(0.0, 0.0) == 1.0
    with pytest.raises(ValueError, match='Fractional power'):
        power(-2.0, 0.5)
    with pytest.raises(ZeroDivisionError, match='negative power'):
        power(0.0, -1.0)
    with pytest.raises(OverflowError):
        power(1e308, 2.0)


def test_shared_inputs_match_product_csvs():
    model = mx.read_model(MODEL)
    try:
        tables = {
            'model_point_table': ('model_point_table.csv', 'point_id'),
            'mort_table': ('mort_table.csv', ['age', 'sex']),
            'surr_charge_table': ('surr_charge_table.csv', ['schedule', 'contract_year']),
            'surr_charge_age_cap_table': ('surr_charge_age_cap.csv', 'age'),
            'rate_scenario': ('rate_scenario.csv', ['scenario_id', 't']),
            'withdrawal_table': ('withdrawal_table.csv', ['wd_schedule_id', 't']),
            'mva_factor_table': ('mva_factor_table.csv', 'years_remaining'),
        }
        for cell, (filename, index) in tables.items():
            expected = pd.read_csv(MODEL.parent / filename, index_col=index)
            pd.testing.assert_frame_equal(getattr(model.Data, cell)(), expected)
    finally:
        model.close()


def test_live_and_exported_helper_contract(tmp_path, monkeypatch):
    model = mx.read_model(MODEL)
    try:
        expected = {}
        for policy in range(1, 8):
            p = model.Projection[policy]
            cashflows = np.array([p.net_cf(t) for t in range(p.proj_len())])
            report = p.result_cf()
            assert np.isfinite(cashflows).all()
            assert np.isfinite(report.to_numpy()).all()
            expected[policy] = (cashflows, report.copy(), p.scenario_id())
        model.export(tmp_path / 'myga_helpers_export')
    finally:
        model.close()

    monkeypatch.syspath_prepend(str(tmp_path))
    exported = importlib.import_module('myga_helpers_export').mx_model
    try:
        for policy, (cashflows, report, scenario) in expected.items():
            p = exported.Projection[policy]
            # Report first reverses the live calculation/report order above.
            pd.testing.assert_frame_equal(p.result_cf(), report, rtol=1e-9, atol=1e-7)
            actual = np.array([p.net_cf(t) for t in range(p.proj_len())])
            assert np.isfinite(actual).all()
            np.testing.assert_allclose(actual, cashflows, rtol=1e-9, atol=1e-7)
            assert p.scenario_id() == scenario
            assert isinstance(p.sex(), Sex)
            assert p.av_pp_at(0, AccountTiming.BEF_WD) == p.av_pp_init()
            assert p.claims(0, Claim.TOTAL) == p.claims(0)
            assert exported.Projection[policy, scenario].scenario_id() == scenario
            pd.testing.assert_frame_equal(p.result_cf(), report, rtol=1e-9, atol=1e-7)
    finally:
        for name in tuple(sys.modules):
            if name == 'myga_helpers_export' or name.startswith('myga_helpers_export.'):
                del sys.modules[name]
