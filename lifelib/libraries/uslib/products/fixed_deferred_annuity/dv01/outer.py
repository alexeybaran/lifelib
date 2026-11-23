"""Collect-based portfolio results and interest-rate sensitivities."""


def scenario_ids():
    return tuple(range(1, ESG.scen_size() + 1))


def actual_cashflows(scen_id):
    return Actual.collect(scen_id).sum.net_cf


def liability_pv(month, scen_id, key):
    return Valuation.collect(month, scen_id, key).sum.liability_pv


def base_liability_pv(month, scen_id):
    return Valuation.collect(month, scen_id, -1).sum.liability_pv


def base_cashflows(month, scen_id):
    return Valuation.collect(month, scen_id, -1).sum.net_cf


def shocked_liability_pv(month, scen_id, key):
    return Valuation.collect(month, scen_id, key).sum.liability_pv


def dv01(month, scen_id, key):
    return base_liability_pv(month, scen_id) - shocked_liability_pv(month, scen_id, key)


def cs01(month, scen_id, key):
    base_cashflow = base_cashflows(month, scen_id)
    market = Market(month + 1, scen_id, key)
    discounts = [market.price(month + k + 2) for k in base_cashflow]
    liability = float(-np.dot(tuple(base_cashflow.values()), discounts))
    return base_liability_pv(month, scen_id) - liability
