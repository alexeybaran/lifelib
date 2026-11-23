"""G2++ price selection and MYGA restart boundaries."""

from pathlib import Path

import numpy as np
import pytest
from modelx.core.errors import FormulaError

from .model import OPENING_COLUMNS, build_model


def expected_price(engine, as_of, maturity, scenario, shock=-1):
    """Select a raw engine price, then apply a spot-yield bump independently."""
    price = float(engine.P_t_T(as_of, maturity)[scenario - 1])
    if shock == -1 or maturity == as_of:
        return price
    maturity_years = (maturity - as_of) / 12
    weight = np.interp(maturity_years, [*range(1, 11), 15, 20], np.arange(12) == shock)
    zero = price ** (-1 / maturity_years) - 1
    return (1 + zero + 1e-4 * weight) ** -maturity_years


def expected_rate(engine, as_of, forward, tenor, scenario, shock=-1):
    start = expected_price(engine, as_of, forward, scenario, shock)
    end = expected_price(engine, as_of, forward + tenor, scenario, shock)
    return (start / end) ** (12 / tenor) - 1


@pytest.fixture
def model():
    m = build_model(route='direct', outer_months=121, valuation_months=(12, 60, 61))
    try:
        yield m
    finally:
        m.close()


def test_rate_ranges_and_month_end_mva_quote(model):
    from .native_spec import native_spec
    market_spec = native_spec(model)["spaces"]["Market"]["cells_param_size"]
    assert market_spec["tenor_month", "forward_month"] == (61, 1202)
    assert market_spec["tenor_month"] == 1801  # one-argument shock weight
    actual = model.Actual[1, 1]
    valuation = model.Valuation[0, 1, 1, -1]
    for month in (0, 1, 59):
        tenor = 59 - month
        assert actual.competitor_tenor(month) == tenor + 1
        assert round(12 * actual.mva_term(month)) == tenor
        assert actual.mva_ref_yield(month) == actual.market(month).rate(tenor, month)
        market = actual.market(0) if month == 0 else valuation.market()
        assert valuation.mva_ref_yield(month) == market.rate(tenor, month)


def test_market_prices_select_real_esg_paths_and_shock_both_forward_endpoints(model):
    as_of = 60
    raw = model.ESG.P_t_T(as_of, as_of + 60)
    assert raw.shape == (model.ESG.scen_size(),)
    assert model.Outer.scenario_ids() == tuple(range(1, len(raw) + 1))
    assert raw[0] != raw[1]
    for scenario in (1, 2):
        base = model.Market(as_of, scenario, -1)
        assert base.base_price(as_of + 60) == raw[scenario - 1]
        for shock in range(-1, 12):
            market = model.Market(as_of, scenario, shock)
            for offset in (0, 5, 12, 24, 31, 60, 98, 120, 240, 267):
                maturity = as_of + offset
                assert market.price(maturity) == pytest.approx(
                    expected_price(model.ESG, as_of, maturity, scenario, shock), rel=1e-13)
            assert market.rate(60, as_of) == pytest.approx(
                expected_rate(model.ESG, as_of, as_of, 60, scenario, shock), abs=1e-13)
            assert market.rate(60, as_of + 60) == pytest.approx(
                expected_rate(model.ESG, as_of, as_of + 60, 60, scenario, shock), abs=1e-13)
        bumped = model.Market(as_of, scenario, 4)
        assert bumped.rate(60, as_of) - base.rate(60, as_of) == pytest.approx(1e-4)
        assert bumped.rate(60, as_of + 60) != base.rate(60, as_of + 60)


def test_default_esg_workbook_resolves_after_relocation(model, tmp_path):
    workbook = Path(model.ESG.input_path())
    assert workbook.name == 'g2pp_input.xlsx'
    assert workbook.is_file()
    model.path = tmp_path / 'relocated_model'
    model.ESG.input_path.clear()
    assert Path(model.ESG.input_path()) == workbook
    assert model.ESG.P_t_T(12, 72).shape == (model.ESG.scen_size(),)


@pytest.mark.parametrize('scenario', [1, 2])
def test_actual_and_valuation_follow_same_path_across_a_renewal_cut(model, scenario):
    policy, cut, next_renewal = 1, 60, 120
    first_projected = cut + 1
    actual = model.Actual(policy, scenario)
    issue = actual.model_point()
    assert actual.credit_rate(12) == issue['declared_rate_initial']
    assert actual.mva_ref_yield_locked(12) == issue['mva_ref_yield_at_issue']
    assert actual.market(12) is model.Market(12, scenario, -1)
    assert actual.market(60) is model.Market(60, scenario, -1)

    renewal_quote = expected_rate(model.ESG, cut, cut, 60, scenario)
    observed_spread = actual.renewal_crediting_spread(cut)
    assert actual.mva_ref_yield_locked(cut) == pytest.approx(renewal_quote)
    assert actual.credit_rate(cut) == pytest.approx(max(actual.gmir(), renewal_quote - observed_spread))

    for shock in (-1, 3):
        v = model.Valuation(cut, policy, scenario, shock)
        assert v.market() is model.Market(first_projected, scenario, shock)
        for name in OPENING_COLUMNS:
            assert getattr(v, name)(first_projected) == getattr(actual, name)(first_projected), name
        for field in ('av_pp', 'mgsv_pp', 'interest_credited_pp', 'prem_accum_gmir_pp',
                      'free_wd_remain', 'tax_basis_pp', 'net_cf', 'market_rate', 'renewal_quote',
                      'mva_ref_yield', 'mva_fixing_yield'):
            for t in (cut - 1, cut):
                assert getattr(v, field)(t) == getattr(actual, field)(t), (field, t)
        assert v.cashflow_at_offset(0) == v.net_cf(first_projected) == v.contract_net_cf(first_projected)
        assert v.discount_factor(0) == pytest.approx(
            expected_price(model.ESG, first_projected, first_projected + 1, scenario, shock))
        for t in (cut - 1, cut, cut + 1):
            assert v.credit_rate(t) == actual.credit_rate(t)
            assert v.mva_ref_yield_locked(t) == actual.mva_ref_yield_locked(t)
        quote = expected_rate(model.ESG, first_projected, next_renewal, 60, scenario, shock)
        assert v.renewal_quote(next_renewal) == pytest.approx(quote)
        expected_credit = max(v.gmir(), quote - v.renewal_crediting_spread(next_renewal))
        assert v.credit_rate(next_renewal) == pytest.approx(expected_credit)
        assert v.credit_rate(next_renewal + 1) == pytest.approx(expected_credit)
        assert v.mva_ref_yield_locked(next_renewal + 1) == pytest.approx(quote)
        absolute = next_renewal + 1
        offset = absolute - first_projected
        assert v.market_rate(absolute) == pytest.approx(
            expected_rate(model.ESG, first_projected, absolute, 59, scenario, shock))
        assert v.mva_ref_yield(absolute) == pytest.approx(
            expected_rate(model.ESG, first_projected, absolute, 58, scenario, shock))
        assert v.av_pp(absolute) == pytest.approx(
            v.av_pp_at(absolute, v.AvTiming.BEF_INV) * (1 + expected_credit) ** (1 / 12))
        assert v.cashflow_at_offset(offset) == v.net_cf(absolute)
        assert v.discount_factor(offset) == pytest.approx(
            expected_price(model.ESG, first_projected, absolute + 1, scenario, shock))

    after_cut = model.Valuation(cut + 1, policy, scenario, 3)
    assert after_cut.credit_rate(cut + 1) == actual.credit_rate(cut)
    assert after_cut.mva_ref_yield_locked(cut + 1) == actual.mva_ref_yield_locked(cut)
    for name in OPENING_COLUMNS:
        assert getattr(after_cut, name)(cut + 2) == getattr(actual, name)(cut + 2), name


def test_guarantee_floor_is_applied_after_subtracting_renewal_spread(model):
    model.Actual.renewal_spread = 0.10
    model.Valuation.renewal_spread = 0.10
    actual = model.Actual(1, 1)
    v = model.Valuation(60, 1, 1, 3)
    assert actual.renewal_crediting_spread(60) == 0.10
    assert actual.renewal_quote(60) - 0.10 < actual.gmir()
    assert actual.credit_rate(60) == actual.gmir()
    assert v.credit_rate(60) == actual.credit_rate(60)
    assert v.renewal_crediting_spread(120) == 0.10
    assert v.renewal_quote(120) - 0.10 < v.gmir()
    assert v.credit_rate(120) == v.gmir()


def test_annual_renewal_uses_one_year_for_credit_and_five_years_for_mva(model):
    actual = model.Actual(3, 2)
    cut = 60
    observed_credit = expected_rate(model.ESG, cut, cut, 12, 2)
    observed_mva = expected_rate(model.ESG, cut, cut, 60, 2)
    assert actual.credit_rate(cut) == pytest.approx(max(actual.gmir(), observed_credit))
    assert actual.mva_ref_yield_locked(cut) == pytest.approx(observed_mva)
    v = model.Valuation(cut, 3, 2, 3)
    assert v.credit_rate(cut + 1) == actual.credit_rate(cut)
    assert v.mva_ref_yield_locked(cut + 1) == actual.mva_ref_yield_locked(cut)
    assert v.competitor_tenor(cut + 1) == 12
    next_credit = expected_rate(model.ESG, cut + 1, 72, 12, 2, 3)
    assert v.credit_rate(72) == pytest.approx(max(v.gmir(), next_credit))
    assert v.mva_ref_yield_locked(72) == actual.mva_ref_yield_locked(cut)

@pytest.mark.parametrize("raw", ["tenor_months\n", "years\n12\n", "tenor_months\n0\n",
                                 "tenor_months\n12\n12\n", "tenor_months\n24\n12\n",
                                 "tenor_months\n12.5\n"])
def test_invalid_shock_file_is_rejected(model, tmp_path, raw):
    (tmp_path / "shock_steps.csv").write_text(raw, encoding="utf-8")
    model.Data.input_dir.formula = lambda: directory
    model.Data.directory = tmp_path
    with pytest.raises(FormulaError, match="ValueError: shock"):
        model.Data.shock_key_months()
