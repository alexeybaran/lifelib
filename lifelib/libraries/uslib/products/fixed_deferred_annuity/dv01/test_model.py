"""MYGA data sharing and policy-specific market selection."""
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


def test_policy_tables_preloaded_and_shock_grid_read_once(monkeypatch):
    count = []
    original = pd.read_csv
    def read(*a, **kw):
        count.append(str(a[0]))
        return original(*a, **kw)
    monkeypatch.setattr(pd, 'read_csv', read)
    m = build_model(route='direct',model_name='ReadsTest')
    try:
        assert len(count) == 6
        assert m.Data.shock_key_months() == [*range(12, 121, 12), 180, 240]
        for i in range(1,8):
            m.Actual[i, 1].net_cf(1)
            m.Actual[i, 1].mort_rate_mth(60)
        assert [Path(name).name for name in count].count('shock_steps.csv') == 1
        assert len(count) == 7
    finally:
        m.close()


def test_scenario_result_shared_across_policies(model):
    first, second = model.Actual[1, 1], model.Actual[2, 1]
    assert first.market(12) is second.market(12)
    assert first.market(12) is not model.Actual[1, 2].market(12)
    value = first.market(12).rate(60, 12)
    entries = len(first.market(12).rate)
    assert second.market(12).rate(60, 12) == value
    assert len(first.market(12).rate) == entries
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
        assert linked.Actual[1, 1].net_cf(12) == model.Actual[1, 1].net_cf(12)
        assert linked.Data.surrender_rate('initial', 1) == model.Data.surrender_rate('initial', 1)
        assert linked.Data.mva_factor_hi(0.5) == model.Data.mva_factor_hi(0.5)
    finally:
        linked.close()
        myga.close()


def test_issue_state_uses_booked_rates_with_dv01_market(model):
    for policy_id, policy in model.Data.model_point_table().iterrows():
        actual = model.Actual(int(policy_id), 1)
        assert actual.policy_state(0)[7:] == (
            policy['declared_rate_initial'], policy['mva_ref_yield_at_issue'])
        assert actual.market(0) is model.Market(0, 1, -1)
        assert actual.mva_ref_yield_locked(0) != actual.mva_fixing_yield(0)


def test_one_valuation_uses_its_own_market(model):
    selected = model.Valuation(12, 1, 1, -1)
    sibling = model.Valuation(12, 2, 1, -1)
    selected_before = selected.market_rate(12), selected.cashflow_at_offset(0), selected.discount_factor(0)
    sibling_before = sibling.market_rate(12), sibling.cashflow_at_offset(0), sibling.discount_factor(0)
    assert selected.market() is sibling.market()

    market = model.new_space('MarketOverride')
    market.new_cells('rate', 'lambda tenor_month, forward_month: 0.09')
    market.new_cells('price', 'lambda maturity_month: 0.99 ** (maturity_month - 12)')
    selected.market[()] = market

    assert selected.market() is market
    assert selected.market_rate(12) == 0.09 != selected_before[0]
    assert selected.cashflow_at_offset(0) != selected_before[1]
    assert selected.discount_factor(0) == 0.99 != selected_before[2]
    assert (sibling.market_rate(12), sibling.cashflow_at_offset(0), sibling.discount_factor(0)) == sibling_before
    del model.Valuation[12, 2, 1, -1]
    sibling = model.Valuation(12, 2, 1, -1)
    assert (sibling.market_rate(12), sibling.cashflow_at_offset(0), sibling.discount_factor(0)) == sibling_before


def test_different_policy_rules_still_apply(model):
    assert model.Actual[3, 1].renewal_architecture() == Renewal.annual_redeclare
    assert model.Actual[1, 1].renewal_architecture() == Renewal.rollover
    assert model.Actual[1, 1].mva_term(61) > 0
    assert model.Actual[3, 1].mva_term(61) == 0
    assert model.Actual[1, 1].wd_scheduled_pp(12) > 0
    assert model.Actual[2, 1].wd_scheduled_pp(12) == 0


def test_changed_policy_input_before_calculation(model):
    table = model.Data.policy_table.copy()
    table.loc[1,'premium'] = 175000.0
    model.Data.policy_table = table
    assert model.Actual[1, 1].premium_pp() == 175000.0
    assert model.Actual[1, 1].initial_state()[0] == 175000.0
    assert model.Actual[2, 1].initial_state()[0] == 100000.0


def test_existing_cell_cache_semantics(model):
    first = model.Actual[1, 1].premium_pp()
    table = model.Data.policy_table.copy()
    table.loc[1,'premium'] = 175000.0
    model.Data.policy_table = table
    # Live modelx tracks dependencies and invalidates here; compiled behavior is
    # separately qualified, and we do not infer its behavior from this fixture.
    assert model.Actual[1, 1].premium_pp() == 175000.0
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
        assert m.Actual[105, 1].premium_pp() == m.Actual[7, 1].premium_pp()
        assert m.Actual[105, 1].initial_state() == m.Actual[7, 1].initial_state()
    finally:
        m.close()


def test_bad_policy_ids_rejected():
    table=pd.DataFrame({'premium':[1.,2.]},index=[1,1])
    with pytest.raises(ValueError,match='unique'):
        build_model(policy_table=table)


def test_table_lookups_shared_by_economic_key(model):
    first, second = model.Actual[1, 1], model.Actual[2, 1]
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
    """One-policy collect exactly matches the item's own results on each path."""
    folder = Path(__file__).resolve().parent.parent
    table = pd.read_csv(folder/'model_point_table.csv', index_col='point_id').iloc[:1].copy()
    table.loc[1, 'age_at_entry'] = 99
    months = (0, 3, 6, 9)
    m = build_model(route='collect', policy_table=table, model_name='OnePolicySweep',
                    outer_months=12, valuation_months=months)
    try:
        m.collect_workers = 4
        assert m.Valuation.policy_ids() == (1,)
        for month in months:
            for shock in (-1, 3):
                aggregate = m.Valuation.collect(month, 2, shock).sum
                valuation = m.Valuation(month, 1, 2, shock)
                assert aggregate.liability_pv == valuation.liability_pv()
                assert aggregate.net_cf[0] == valuation.net_cf(month)
                assert aggregate.net_cf[1] == valuation.net_cf(month + 1)
    finally:
        m.close()
