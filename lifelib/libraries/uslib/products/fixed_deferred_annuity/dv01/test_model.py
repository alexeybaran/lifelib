"""Focused data-sharing contracts; full economic validation lives in toolkit."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
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
        assert len(count) == 5
        for i in range(1,8):
            m.Actual[i].net_cf(1)
            m.Actual[i].mort(60)
        assert len(count) == 5
    finally:
        m.close()


def test_scenario_result_shared_across_policies(model):
    first, second = model.Actual[1], model.Actual[2]
    assert first.Market is second.Market
    value = first.Market.rate(1,5.0)
    entries = len(first.Market.rate)
    assert second.Market.rate(1,5.0) == value
    assert len(first.Market.rate) == entries
    assert first.state is not second.state


def test_different_policy_rules_still_apply(model):
    assert model.Actual[3].annual_redeclare()
    assert not model.Actual[1].annual_redeclare()
    assert model.Actual[1].mva_term(61) > 0
    assert model.Actual[3].mva_term(61) == 0
    assert model.Actual[1].wd(12) > 0
    assert model.Actual[2].wd(12) == 0


def test_changed_policy_input_before_calculation(model):
    table = model.Data.policy_table.copy()
    table.loc[1,'premium'] = 175000.0
    model.Data.policy_table = table
    assert model.Actual[1].premium_pp() == 175000.0
    assert model.Actual[1].state_value(0) == 175000.0
    assert model.Actual[2].state_value(0) == 100000.0


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
        assert m.Actual.policy_ids == tuple(range(1,106))
        # Structural/one-step check only; never execute a 105-policy live projection.
        assert m.Actual[105].premium_pp() == m.Actual[7].premium_pp()
        assert m.Actual[105].state is not m.Actual[7].state
    finally:
        m.close()


def test_bad_policy_ids_rejected():
    table=pd.DataFrame({'premium':[1.,2.]},index=[1,1])
    with pytest.raises(ValueError,match='unique'):
        build_model(policy_table=table)
