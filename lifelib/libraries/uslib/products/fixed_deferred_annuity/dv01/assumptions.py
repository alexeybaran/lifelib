"""Readable policy assumptions, evaluated on demand from shared input tables.

Time t is relative to this projection; month(t) is duration since issue.
The economic rules match the retained DV01 demo, including its 480-month term.
"""

def month(t):
    return valuation_month + t


def age(t):
    return age_at_entry() + month(t) // 12


def gp_index(t):
    return month(t) // 60 + 1


def annual_redeclare():
    return renewal_architecture() == 'annual_redeclare'


def mva_term(t):
    if month(t) >= 480 or (annual_redeclare() and month(t) >= 60):
        return 0.0
    return (60 * gp_index(t) - (month(t) + 1)) / 12.0


def market_tenor(t):
    if annual_redeclare() and month(t) >= 60:
        return 1.0
    return (60 * gp_index(t) - month(t)) / 12.0


def gp_window(t):
    if month(t) >= 480:
        return 0.0
    if annual_redeclare():
        return 1.0 if month(t) == 60 else 0.0
    return 1.0 if month(t) > 0 and month(t) % 60 == 0 else 0.0


def redeclare(t):
    if month(t) >= 480:
        return 0.0
    if annual_redeclare():
        return 1.0 if month(t) >= 60 and month(t) % 12 == 0 else 0.0
    return gp_window(t)


def anniversary(t):
    return 1.0 if 0 < month(t) < 480 and month(t) % 12 == 0 else 0.0


def mort(t):
    if month(t) >= 480 or age(t) > 99:
        return 0.0
    annual = Data.mortality_rate(age(t), sex())
    return 1.0 - (1.0 - annual) ** (1.0 / 12.0)


def wd(t):
    if month(t) >= 480:
        return 0.0
    return Data.withdrawal_amount(wd_schedule_id(), month(t))


def surr_charge(t):
    if month(t) >= 480 or gp_window(t) > 0.5:
        return 0.0
    if gp_index(t) > 1 and annual_redeclare():
        return 0.0
    schedule = 'initial' if gp_index(t) <= 1 else 'renewal'
    year = (month(t) // 12) % 5 + 1
    rate = Data.surrender_rate(schedule, year)
    if age(t) >= 94:
        # Keep the demo's arithmetic order, including cap rounding.
        rate = min(rate, max(0.0, 0.04 - 0.01 * (age(t) - 94)))
    return rate


def lapse_base(t):
    if month(t) >= 480:
        return 0.0
    year = month(t) // 12 + 1
    if annual_redeclare():
        if year <= 5:
            return 0.01
        if year == 6:
            return 0.75
        if year == 7:
            return 0.10
        if year == 8:
            return 0.075
        return 0.03
    return 0.75 if year > 5 and (year - 1) % 5 == 0 else 0.01


def lapse_power(t):
    if month(t) >= 480:
        return 0.0
    return 2.0 if month(t) // 12 + 1 <= 5 else 2.5


def inflation(t):
    if month(t) >= 480:
        return 0.0
    return 1.025 ** (month(t) // 12)


def premium(t):
    return premium_pp() if month(t) == 0 else 0.0


def maturity(t):
    return 1.0 if month(t) == 479 else 0.0


def mva_factor_lo(t):
    return Data.mva_factor_lo(mva_term(t))


def mva_factor_hi(t):
    return Data.mva_factor_hi(mva_term(t))


def market_rate(t):
    return Market.rate(t, market_tenor(t)) if month(t) < 480 else 0.0


def mva_ref_yield(t):
    return Market.rate(t, mva_term(t)) if month(t) < 480 else 0.0


def declaration_yield(t):
    return Market.rate(t, 1.0 if annual_redeclare() else 5.0) if month(t) < 480 else 0.0


def mva_lock_yield(t):
    return Market.rate(t, 5.0) if month(t) < 480 else 0.0


def discount_factor(t):
    return Market.discount_factor(t)


def credit_rate(t):
    if t == 0:
        return state_value(7)
    if redeclare(t) > 0.5:
        return max(gmir(), declaration_yield(t) - Market.spread(t))
    return credit_rate(t - 1)
