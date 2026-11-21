"""Shared curve preparation and evaluation, independent of policy state."""


def monthly_inputs():
    return helpers.monthly_outer_scenario(Data.annual_curves, Data.annual_spreads, months=outer_months)


def monthly_curves():
    return monthly_inputs()[0]


def monthly_spreads():
    return monthly_inputs()[1]


def nodes(curve_index, annual):
    if annual:
        return Data.annual_curves[curve_index]
    return monthly_curves()[curve_index]


def node_discounts(curve_index, annual):
    curve = nodes(curve_index, annual)
    return tuple((1.0 + curve[i]) ** (-tenors[i]) for i in range(len(tenors)))


def curve_df(curve_index, annual, tau):
    if tau <= 0.0:
        return 1.0
    if tau <= 1.0:
        return (1.0 + float(nodes(curve_index, annual)[0])) ** (-tau)
    dfs = node_discounts(curve_index, annual)
    for i in range(1, len(tenors)):
        right_tenor = float(tenors[i])
        if tau <= right_tenor:
            left_tenor = float(tenors[i - 1])
            weight = (tau - left_tenor) / (right_tenor - left_tenor)
            left_df = float(dfs[i - 1])
            right_df = float(dfs[i])
            return left_df * (right_df / left_df) ** weight
    last = len(tenors) - 1
    last_df = float(dfs[last])
    prior_df = float(dfs[last - 1])
    last_tenor = float(tenors[last])
    prior_tenor = float(tenors[last - 1])
    return last_df * (last_df / prior_df) ** ((tau - last_tenor) / (last_tenor - prior_tenor))


def zero_yield(curve_index, annual, tau):
    if tau <= 0.0:
        return float(nodes(curve_index, annual)[0])
    return curve_df(curve_index, annual, tau) ** (-1.0 / tau) - 1.0


def shock_weight(tau, key_index):
    if not 0 <= key_index < len(tenors):
        raise IndexError('key_index outside KRD node range')
    if key_index == 0:
        if tau <= tenors[0]:
            return 1.0
        if tau >= tenors[1]:
            return 0.0
        return (tenors[1] - tau) / (tenors[1] - tenors[0])
    if key_index == len(tenors) - 1:
        if tau <= tenors[-2]:
            return 0.0
        if tau >= tenors[-1]:
            return 1.0
        return (tau - tenors[-2]) / (tenors[-1] - tenors[-2])
    left = float(tenors[key_index - 1])
    key = float(tenors[key_index])
    right = float(tenors[key_index + 1])
    if tau <= left or tau >= right:
        return 0.0
    if tau <= key:
        return (tau - left) / (key - left)
    return (right - tau) / (right - key)


def shocked_zero_yield(curve_index, annual, tau, shock):
    return zero_yield(curve_index, annual, tau) + shock_bp * shock_weight(tau, shock)


def discount_factor(curve_index, annual, tau, shock=-1):
    if tau <= 0.0:
        return 1.0
    z = zero_yield(curve_index, annual, tau)
    if shock != -1:
        z += shock_bp * shock_weight(tau, shock)
    return (1.0 + z) ** (-tau)


def forward_yield(curve_index, annual, start_tau, tenor, shock=-1):
    if tenor <= 0.0:
        return 0.0
    df0 = discount_factor(curve_index, annual, start_tau, shock)
    df1 = discount_factor(curve_index, annual, start_tau + tenor, shock)
    return (df0 / df1) ** (1.0 / tenor) - 1.0


def discount_factors(curve_index, shock=-1):
    return np.asarray([
        discount_factor(curve_index, True, (t + 1.0) / 12.0, shock)
        for t in range(valuation_horizon)
    ], dtype=np.float64)
