"""Annual portfolio sensitivities on individual generated ESG paths."""

from numbers import Integral

import pandas as pd


def annual_risk_report(model, num_scenarios, annual_steps):
    """Return (dv01, cs01) DataFrames for ESG paths 1..N and years 0..annual_steps."""
    for name, value, minimum in (
        ('num_scenarios', num_scenarios, 1), ('annual_steps', annual_steps, 0)
    ):
        if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
            raise ValueError(f'{name} must be an integer >= {minimum}')
    if num_scenarios > model.ESG.scen_size():
        raise ValueError('num_scenarios exceeds the number of generated ESG paths')
    if 12 * int(annual_steps) >= model.ESG.step_size():
        raise ValueError('last annual close is outside the generated ESG time grid')

    index = pd.MultiIndex.from_product(
        [range(1, num_scenarios + 1), range(annual_steps + 1)], names=['scenario', 'year']
    )
    tenors = pd.Index(model.Data.shock_key_months(), name='tenor_months')
    dv01_rows, cs01_rows = [], []
    for scenario, year in index:
        month = 12 * year
        dv01_rows.append([model.Outer.dv01(month, scenario, key) for key in range(len(tenors))])
        cs01_rows.append([model.Outer.cs01(month, scenario, key) for key in range(len(tenors))])
    return (pd.DataFrame(dv01_rows, index=index, columns=tenors),
            pd.DataFrame(cs01_rows, index=index, columns=tenors))
