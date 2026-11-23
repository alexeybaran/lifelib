"""Portfolio aggregations through individual ItemSpaces for the direct route."""


def actual_cashflows(scen_id):
    result = {t: 0.0 for t in Actual.projection_months}
    for p in Actual.policy_ids():
        projection = Actual[p, scen_id]
        for t in Actual.projection_months:
            result[t] += projection.net_cf(t)
    return result


def liability_pv(month, scen_id, key):
    total = 0.0
    for p in Valuation.policy_ids():
        total += Valuation(month, p, scen_id, key).liability_pv()
    return total


def base_liability_pv(month, scen_id):
    return liability_pv(month, scen_id, -1)


def base_cashflows(month, scen_id):
    offsets = Valuation.projection_months(month)
    result = {k: 0.0 for k in offsets}
    for p in Valuation.policy_ids():
        projection = Valuation(month, p, scen_id, -1)
        for k in offsets:
            result[k] += projection.cashflow_at_offset(k)
    return result


def shocked_liability_pv(month, scen_id, key):
    return liability_pv(month, scen_id, key)
