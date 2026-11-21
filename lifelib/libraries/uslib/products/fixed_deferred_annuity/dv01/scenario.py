"""Shared market calculations: no policy identity or policy state here."""

def year():
    """The scenario year of the valuation date; dates after the last annual point hold it, as the
    monthly scenario does."""
    return min(valuation_month // 12, len(Data.annual_spreads) - 1)


def curve(t):
    if forward_project:
        return Curves.nodes(year(), True)
    return Curves.nodes(t, False)


def spread(t):
    if forward_project:
        return float(Data.annual_spreads[year()])
    return float(Curves.monthly_spreads()[t])


def rate(t, tenor):
    if forward_project:
        if tenor <= 0.0:
            return 0.0
        return Curves.forward_yield(year(), True, t / 12.0, tenor, shock)
    if shock == -1:
        return Curves.zero_yield(t, False, tenor)
    return Curves.shocked_zero_yield(t, False, tenor, shock)


def discount_factor(t):
    curve_index = year() if forward_project else t
    return Curves.discount_factor(curve_index, forward_project, (t + 1.0) / 12.0, shock)
