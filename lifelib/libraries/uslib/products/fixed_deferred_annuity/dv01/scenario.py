"""Shared market calculations: no policy identity or policy state here."""

def curve(t):
    if forward_project:
        return Data.annual_curves[valuation_month // 12]
    return Data.monthly_curves()[t]


def spread(t):
    if forward_project:
        return float(Data.annual_spreads[valuation_month // 12])
    return float(Data.monthly_spreads()[t])


def rate(t, tenor):
    key = None if shock == -1 else shock
    if forward_project:
        if tenor <= 0.0:
            return 0.0
        return curves.forward_yield(curve(t), t / 12.0, tenor, key_index=key)
    if key is None:
        return curves.curve_yield(curve(t), tenor)
    return curves.shocked_zero_yield(curve(t), tenor, key)


def discount_factor(t):
    key = None if shock == -1 else shock
    return curves.discount_factor(curve(t), (t + 1.0) / 12.0, key_index=key)
