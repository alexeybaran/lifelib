"""Focused data-sharing contracts; full economic validation lives in toolkit."""
from pathlib import Path
import pandas as pd
import pytest
from lifelib.libraries.uslib.products.fixed_deferred_annuity.enums import Renewal
from .model import build_model


@pytest.fixture
def model():
    m = build_model(route='direct', model_name='SharedDataTest')
    try:
        yield m
    finally:
        m.close()


def test_data_files_only_read_at_construction(monkeypatch):
    count = []
    original = pd.read_csv
    def read(*a, **kw):
        count.append(str(a[0]))
        return original(*a, **kw)
    monkeypatch.setattr(pd, 'read_csv', read)
    m = build_model(route='direct',model_name='ReadsTest')
    try:
        assert len(count) == 6
        for i in range(1,8):
            m.Actual[i].net_cf(1)
            m.Actual[i].mort_rate_mth(60)
        assert len(count) == 6
    finally:
        m.close()


def test_scenario_result_shared_across_policies(model):
    first, second = model.Actual[1], model.Actual[2]
    assert first.market() is second.market()
    value = first.market().rate(1,5.0)
    entries = len(first.market().rate)
    assert second.market().rate(1,5.0) == value
    assert len(first.market().rate) == entries
    assert first.initial_state() is not second.initial_state()


def test_saved_myga_data_cells_are_used_by_dv01(model):
    import modelx as mx
    source = Path(__file__).resolve().parents[1] / 'MYGA_US_S'
    myga = mx.read_model(source, name='SharedDataSource')
    linked = build_model(route='direct', model_name='SharedDataLinked', myga_model=source)
    try:
        for name in ('model_point_table', 'mort_table', 'withdrawal_table',
                     'surr_charge_table', 'surr_charge_age_cap_table', 'mva_factor_table'):
            assert linked.Data.cells[name].formula.source == myga.Data.cells[name].formula.source
        assert linked.Actual.policy_ids() == model.Actual.policy_ids()
        assert linked.Actual[1].net_cf(12) == model.Actual[1].net_cf(12)
        assert linked.Data.surrender_rate('initial', 1) == model.Data.surrender_rate('initial', 1)
        assert linked.Data.mva_factor_hi(0.5) == model.Data.mva_factor_hi(0.5)
    finally:
        linked.close()
        myga.close()


def test_issue_state_uses_booked_rates_with_dv01_market(model):
    for policy_id, policy in model.Data.model_point_table().iterrows():
        actual = model.Actual(policy_id=int(policy_id))
        assert actual.policy_state(0)[7:] == (
            policy['declared_rate_initial'], policy['mva_ref_yield_at_issue'])
        assert actual.market() is model.Scenarios(0, False, -1)
        assert actual.mva_ref_yield_locked(0) != actual.mva_fixing_yield(0)


def test_one_valuation_uses_its_own_market(model):
    selected = model.Valuation(12, 1, -1)
    sibling = model.Valuation(12, 2, -1)
    selected_before = selected.market_rate(12), selected.cashflow_at_offset(0), selected.discount_factor(0)
    sibling_before = sibling.market_rate(12), sibling.cashflow_at_offset(0), sibling.discount_factor(0)
    assert selected.market() is sibling.market()

    market = model.new_space('MarketOverride')
    market.new_cells('rate', 'lambda t, tenor: 0.09')
    market.new_cells('spread', 'lambda t: 0.005')
    market.new_cells('discount_factor', 'lambda t: 0.99 ** (t + 1)')
    selected.market[()] = market

    assert selected.market() is market
    assert selected.market_rate(12) == 0.09 != selected_before[0]
    assert selected.cashflow_at_offset(0) != selected_before[1]
    assert selected.discount_factor(0) == 0.99 != selected_before[2]
    assert (sibling.market_rate(12), sibling.cashflow_at_offset(0), sibling.discount_factor(0)) == sibling_before
    del model.Valuation[12, 2, -1]
    sibling = model.Valuation(12, 2, -1)
    assert (sibling.market_rate(12), sibling.cashflow_at_offset(0), sibling.discount_factor(0)) == sibling_before


@pytest.mark.parametrize('policy_id,renewal_tenor', [(1, 5.0), (3, 1.0)])
def test_restart_uses_booked_rates_at_cut_and_item_rates_after_cut(policy_id, renewal_tenor):
    m = build_model(route='direct', model_name='RestartRates', outer_months=73)
    try:
        observed = m.Actual[policy_id]
        prospective = m.Valuation(59, policy_id, 3)
        at_renewal = m.Valuation(60, policy_id, 3)
        assert 'ValuationContract' not in m.Valuation.spaces
        market = m.new_space('RestartOverride')
        market.new_cells('rate', 'lambda k, tenor: 0.08 + k / 1000 + tenor / 1000')
        market.new_cells('spread', 'lambda k: 0.005 + k / 2000')
        for valuation in (prospective, at_renewal):
            valuation.market[()] = market
        assert at_renewal.market_rate(59) == observed.market_rate(59)
        assert at_renewal.mva_ref_yield(59) == observed.mva_ref_yield(59)
        assert at_renewal.credit_rate(59) == observed.credit_rate(59)
        assert at_renewal.mva_ref_yield_locked(59) == observed.mva_ref_yield_locked(59)
        assert at_renewal.initial_state() == observed.policy_state(60)
        assert at_renewal.state_at_offset(0) == observed.policy_state(60)
        assert at_renewal.credit_rate(60) == at_renewal.credit_rate(61) == observed.credit_rate(60)
        assert (at_renewal.mva_ref_yield_locked(60) == at_renewal.mva_ref_yield_locked(61)
                == observed.mva_ref_yield_locked(60))
        assert at_renewal.market_rate(60) == market.rate(0, renewal_tenor)
        assert at_renewal.mva_fixing_yield(60) == market.rate(0, 5.0)
        assert at_renewal.market_rate(61) == market.rate(1, at_renewal.competitor_tenor(61))
        assert at_renewal.mva_ref_yield(61) == market.rate(1, at_renewal.mva_term(61))
        assert prospective.credit_rate(60) == market.rate(1, renewal_tenor) - market.spread(1)
        assert prospective.mva_ref_yield_locked(60) == market.rate(1, 5.0)
        next_redeclaration = 120 if renewal_tenor == 5.0 else 72
        offset = next_redeclaration - 60
        assert (at_renewal.credit_rate(next_redeclaration)
                == market.rate(offset, renewal_tenor) - market.spread(offset))
        assert at_renewal.cashflow_at_offset(1) == at_renewal.net_cf(61)
        assert at_renewal.state_at_offset(1) == at_renewal.policy_state(61)
    finally:
        m.close()


def test_different_policy_rules_still_apply(model):
    assert model.Actual[3].renewal_architecture() == Renewal.annual_redeclare
    assert model.Actual[1].renewal_architecture() == Renewal.rollover
    assert model.Actual[1].mva_term(61) > 0
    assert model.Actual[3].mva_term(61) == 0
    assert model.Actual[1].wd_scheduled_pp(12) > 0
    assert model.Actual[2].wd_scheduled_pp(12) == 0


def test_changed_policy_input_before_calculation(model):
    table = model.Data.policy_table.copy()
    table.loc[1,'premium'] = 175000.0
    model.Data.policy_table = table
    assert model.Actual[1].premium_pp() == 175000.0
    assert model.Actual[1].initial_state()[0] == 175000.0
    assert model.Actual[2].initial_state()[0] == 100000.0


def test_existing_cell_cache_semantics(model):
    first = model.Actual[1].premium_pp()
    table = model.Data.policy_table.copy()
    table.loc[1,'premium'] = 175000.0
    model.Data.policy_table = table
    # Live modelx tracks dependencies and invalidates here; compiled behavior is
    # separately qualified, and we do not infer its behavior from this fixture.
    assert model.Actual[1].premium_pp() == 175000.0
    assert first == 100000.0


def test_policy_population_not_fixed_at_seven():
    folder = Path(__file__).resolve().parent.parent
    table = pd.read_csv(folder/'model_point_table.csv',index_col='point_id')
    rows = pd.concat([table]*15,ignore_index=True)
    rows.index = pd.Index(range(1,106),name='point_id')
    m=build_model(route='direct',policy_table=rows,model_name='PopulationTest')
    try:
        assert m.Actual.policy_ids() == tuple(range(1,106))
        # Structural/one-step check only; never execute a 105-policy live projection.
        assert m.Actual[105].premium_pp() == m.Actual[7].premium_pp()
        assert m.Actual[105].initial_state() == m.Actual[7].initial_state()
    finally:
        m.close()


def test_bad_policy_ids_rejected():
    table=pd.DataFrame({'premium':[1.,2.]},index=[1,1])
    with pytest.raises(ValueError,match='unique'):
        build_model(policy_table=table)


def test_table_lookups_shared_by_economic_key(model):
    first, second = model.Actual[1], model.Actual[2]
    first_mort = model.Data.mortality_rate(first.age(1), first.sex())
    entries = len(model.Data.mortality_rate)
    assert model.Data.mortality_rate(second.age(1), second.sex()) == first_mort
    assert len(model.Data.mortality_rate) == entries == 1
    assert first.mort_rate(1) == second.mort_rate(1) == first_mort
    model.Data.mva_factor_lo(first.mva_term(1))
    entries = len(model.Data.mva_factor_lo)
    model.Data.mva_factor_lo(second.mva_term(1))
    assert len(model.Data.mva_factor_lo) == entries == 1


def test_one_policy_collect_per_valuation_date_equals_direct():
    """The per-call case: a book of one policy and a collect per valuation date. Each Valuation.collect(month,
    shock) is one item; its total equals the item's own value exactly, at any collect_workers (one item is
    evaluated serially)."""
    folder = Path(__file__).resolve().parent.parent
    table = pd.read_csv(folder/'model_point_table.csv', index_col='point_id').iloc[:1]
    months = (0, 3, 6, 9)
    m = build_model(route='collect', policy_table=table, model_name='OnePolicySweep',
                    outer_months=12, valuation_months=months)
    try:
        m.collect_workers = 4
        assert m.Valuation.policy_ids() == (1,)
        for month in months:
            for shock in (-1, 3):
                aggregate = m.Valuation.collect(month, shock).sum
                valuation = m.Valuation(month, 1, shock)
                assert aggregate.liability_pv == valuation.liability_pv()
                assert aggregate.net_cf[0] == valuation.net_cf(month)
                assert aggregate.net_cf[1] == valuation.net_cf(month + 1)
    finally:
        m.close()
