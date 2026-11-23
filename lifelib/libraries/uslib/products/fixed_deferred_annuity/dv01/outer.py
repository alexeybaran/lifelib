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


def annual_risk_report(num_scenarios, annual_steps):
    """Return (dv01, cs01) DataFrames for ESG paths 1..N and years 0..annual_steps."""
    for name, value, minimum in (
        ('num_scenarios', num_scenarios, 1), ('annual_steps', annual_steps, 0)
    ):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < minimum:
            raise ValueError(f'{name} must be an integer >= {minimum}')
    if num_scenarios > ESG.scen_size():
        raise ValueError('num_scenarios exceeds the number of generated ESG paths')
    if 12 * int(annual_steps) >= ESG.step_size():
        raise ValueError('last annual close is outside the generated ESG time grid')

    index = pd.MultiIndex.from_product(
        [range(1, num_scenarios + 1), range(annual_steps + 1)], names=['scenario', 'year']
    )
    tenors = pd.Index(data.shock_key_months(), name='tenor_months')
    dv01_rows, cs01_rows = [], []
    for scenario, year in index:
        # The cut is the last completed policy month. At issue none has closed.
        month = 12 * year - 1
        dv01_rows.append([dv01(month, scenario, key) for key in range(len(tenors))])
        cs01_rows.append([cs01(month, scenario, key) for key in range(len(tenors))])
    return (pd.DataFrame(dv01_rows, index=index, columns=tenors),
            pd.DataFrame(cs01_rows, index=index, columns=tenors))
