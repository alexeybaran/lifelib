"""Curve helpers: retained arithmetic from the supplied DV01 example.

No policy data, projection work, file reads or portfolio preparation occurs here.
"""

import numpy as np

KRD_TENORS = (1., 2., 3., 5., 10., 15., 20.)

KRD_BP = 1.e-4

OUTER_YEARS = 10

OUTER_MONTHS = 36

def curve_df(curve_nodes, tau):
    """Annual-effective zero curve with piecewise-flat forward interpolation."""
    curve = np.asarray(curve_nodes, dtype=np.float64)
    tau = float(tau)
    if tau <= 0.0:
        return 1.0
    if tau <= 1.0:
        return float((1.0 + curve[0]) ** (-tau))
    dfs = [(1.0 + curve[i]) ** (-KRD_TENORS[i]) for i in range(7)]
    for i in range(1, 7):
        if tau <= KRD_TENORS[i]:
            w = (tau - KRD_TENORS[i - 1]) / (KRD_TENORS[i] - KRD_TENORS[i - 1])
            return float(dfs[i - 1] * (dfs[i] / dfs[i - 1]) ** w)
    return float(dfs[6] * (dfs[6] / dfs[5]) ** ((tau - 20.0) / 5.0))

def curve_yield(curve_nodes, tau):
    tau = float(tau)
    curve = np.asarray(curve_nodes, dtype=np.float64)
    if tau <= 0.0:
        return float(curve[0])
    df = curve_df(curve, tau)
    return float(df ** (-1.0 / tau) - 1.0)

def outer_scenario():
    """Return the explicit 10-point outer scenario.

    Sovereign zero curves are flat at 1%, 2%, ..., 10% at years 0..9.
    Crediting spread is an explicit scenario rising linearly from 50 bp to
    150 bp over those same 10 annual points.
    """
    levels = np.arange(1.0, 11.0, dtype=np.float64) / 100.0
    curves = np.repeat(levels[:, None], len(KRD_TENORS), axis=1)
    spreads = np.linspace(0.005, 0.015, OUTER_YEARS, dtype=np.float64)
    return (np.ascontiguousarray(curves), np.ascontiguousarray(spreads))

def monthly_outer_scenario(annual_curves, annual_spreads, *, months=OUTER_MONTHS):
    """Linearly interpolate annual scenario points to monthly observation dates.

    The term-structure interpolation *within each curve* remains piecewise-flat
    forward through ``curve_yield``.  This function only interpolates scenario
    evolution through calendar time.  After the last annual point the scenario
    is held flat, which is only relevant after month 108 for the 10-point demo.
    """
    annual_curves = np.asarray(annual_curves, dtype=np.float64)
    annual_spreads = np.asarray(annual_spreads, dtype=np.float64)
    if annual_curves.shape != (OUTER_YEARS, len(KRD_TENORS)):
        raise ValueError('annual_curves must have shape (10, 7)')
    if annual_spreads.shape != (OUTER_YEARS,):
        raise ValueError('annual_spreads must have shape (10,)')
    curves = np.empty((months, len(KRD_TENORS)), dtype=np.float64)
    spreads = np.empty(months, dtype=np.float64)
    for m in range(months):
        y = m / 12.0
        if y >= OUTER_YEARS - 1:
            curves[m] = annual_curves[-1]
            spreads[m] = annual_spreads[-1]
            continue
        lo = int(np.floor(y))
        hi = lo + 1
        w = y - lo
        curves[m] = annual_curves[lo] * (1.0 - w) + annual_curves[hi] * w
        spreads[m] = annual_spreads[lo] * (1.0 - w) + annual_spreads[hi] * w
    return (np.ascontiguousarray(curves), np.ascontiguousarray(spreads))

def krd_weight(tau, key_index):
    """Triangular KRD weight with flat extrapolation at the 1Y/20Y ends."""
    tau = float(tau)
    key_index = int(key_index)
    nodes = KRD_TENORS
    if not 0 <= key_index < len(nodes):
        raise IndexError('key_index outside KRD node range')
    if key_index == 0:
        if tau <= nodes[0]:
            return 1.0
        if tau >= nodes[1]:
            return 0.0
        return (nodes[1] - tau) / (nodes[1] - nodes[0])
    if key_index == len(nodes) - 1:
        if tau <= nodes[-2]:
            return 0.0
        if tau >= nodes[-1]:
            return 1.0
        return (tau - nodes[-2]) / (nodes[-1] - nodes[-2])
    left = nodes[key_index - 1]
    key = nodes[key_index]
    right = nodes[key_index + 1]
    if tau <= left or tau >= right:
        return 0.0
    if tau <= key:
        return (tau - left) / (key - left)
    return (right - tau) / (right - key)

def shocked_zero_yield(curve_nodes, tau, key_index, *, bp=KRD_BP):
    """Base flat-forward zero yield plus a triangular zero-rate KRD shock."""
    return curve_yield(curve_nodes, tau) + float(bp) * krd_weight(tau, key_index)

def discount_factor(curve_nodes, tau, *, key_index=None, bp=KRD_BP):
    """Annual-effective zero-rate discount factor, optionally KRD shocked."""
    tau = float(tau)
    if tau <= 0.0:
        return 1.0
    if key_index is None:
        z = curve_yield(curve_nodes, tau)
    else:
        z = shocked_zero_yield(curve_nodes, tau, key_index, bp=bp)
    return float((1.0 + z) ** (-tau))

def forward_yield(curve_nodes, start_tau, tenor, *, key_index=None, bp=KRD_BP):
    """Annual-effective forward yield implied by today's zero curve.

    ``start_tau`` and ``tenor`` are in years from the valuation date.  A KRD
    shock is first applied to today's zero-yield curve, then the future yield is
    derived from the ratio of shocked discount factors.
    """
    start_tau = float(start_tau)
    tenor = float(tenor)
    if tenor <= 0.0:
        return 0.0
    df0 = discount_factor(curve_nodes, start_tau, key_index=key_index, bp=bp)
    df1 = discount_factor(curve_nodes, start_tau + tenor, key_index=key_index, bp=bp)
    return float((df0 / df1) ** (1.0 / tenor) - 1.0)

def rediscount_liability(cashflows, curve_nodes, *, key_index=None, bp=KRD_BP):
    """Liability value from fixed cashflows under sovereign/spread zero shock."""
    cf = np.asarray(tuple(cashflows), dtype=np.float64)
    dfs = np.asarray([discount_factor(curve_nodes, (t + 1.0) / 12.0, key_index=key_index, bp=bp) for t in range(cf.size)], dtype=np.float64)
    return float(-np.dot(cf, dfs))
