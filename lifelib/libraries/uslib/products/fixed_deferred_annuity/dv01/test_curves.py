import numpy as np
import pytest

from . import curve_helpers
from .model import build_model


@pytest.fixture
def model():
    model = build_model(model_name="SharedCurvesTest")
    # Non-flat curves exercise interpolation and extrapolation.
    nodes = np.array([-0.005, 0.002, 0.009, 0.016, 0.023, 0.027, 0.029])
    model.Data.annual_curves = np.array([nodes + year * 0.001 for year in range(10)])
    try:
        yield model
    finally:
        model.close()


@pytest.mark.parametrize("annual,index", [(True, 0), (True, 2), (False, 0), (False, 17)])
def test_shared_curves_match_original_arithmetic(model, annual, index):
    shared = model.Curves
    nodes = shared.nodes(index, annual)
    for tau in (-0.5, 0.0, 0.25, 1.0, 2.0, 2.5, 5.0, 12.5, 20.0, 27.0, 40.0):
        np.testing.assert_allclose(
            shared.zero_yield(index, annual, tau),
            curve_helpers.curve_yield(nodes, tau), rtol=1e-12, atol=1e-13)
        for shock in (-1, 0, 3, 6):
            np.testing.assert_allclose(
                shared.discount_factor(index, annual, tau, shock),
                curve_helpers.discount_factor(nodes, tau, key_index=None if shock == -1 else shock),
                rtol=1e-12, atol=1e-13)
    for start, tenor in ((0.0, 5.0), (0.5, 4.5), (2.0, 1.0), (24.0, 5.0), (0.0, 0.0)):
        for shock in (-1, 0, 3, 6):
            np.testing.assert_allclose(
                shared.forward_yield(index, annual, start, tenor, shock),
                curve_helpers.forward_yield(nodes, start, tenor, key_index=None if shock == -1 else shock),
                rtol=1e-12, atol=1e-13)


def test_preparation_is_shared_across_policies_and_shocks(model):
    prepared = model.Curves.node_discounts(0, True)
    for shock in (-1, 0, 3):
        market = model.Scenarios(0, True, shock)
        assert market.Curves is model.Curves
        market.rate(24, 5.0)
    assert model.Curves.node_discounts(0, True) is prepared
    assert len(model.Curves.node_discounts) == 1
    assert len(model.Curves.zero_yield) == 2


def test_curve_input_replacement_refreshes_live_cells(model):
    before = model.Curves.zero_yield(0, True, 5.0)
    annual = model.Data.annual_curves.copy()
    annual[0] += 0.01
    model.Data.annual_curves = annual
    after = model.Curves.zero_yield(0, True, 5.0)
    np.testing.assert_allclose(after, curve_helpers.curve_yield(annual[0], 5.0), rtol=1e-12)
    assert after != before
