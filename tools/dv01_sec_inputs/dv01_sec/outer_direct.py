"""Portfolio aggregations through individual ItemSpaces for the direct route (by point index)."""


def actual_cashflows(scen_id):
    result = {t: 0.0 for t in Actual.projection_months}
    for i in Actual.point_indices():
        projection = Actual[i, scen_id]
        for t in Actual.projection_months:
            result[t] += projection.net_cf(t)
    return result


def liability_pv(month, scen_id, key):
    total = 0.0
    for i in Valuation.point_indices():
        total += Valuation(month, i, scen_id, key).liability_pv()
    return total


def base_liability_pv(month, scen_id):
    return liability_pv(month, scen_id, -1)


def base_cashflows(month, scen_id):
    offsets = Valuation.projection_months(month)
    result = {k: 0.0 for k in offsets}
    for i in Valuation.point_indices():
        projection = Valuation(month, i, scen_id, -1)
        for k in offsets:
            result[k] += projection.cashflow_at_offset(k)
    return result


def shocked_liability_pv(month, scen_id, key):
    return liability_pv(month, scen_id, key)
