"""Connect the saved MYGA projection to DV01's Actual market and snapshots."""


def actual_point(policy_id):
    return {'refs': {'point_id': policy_id}}


def competitor_tenor(t):
    term = 12 * guar_period()
    if renewal_architecture() == Renewal.annual_redeclare and t >= term:
        return 1.0
    return (term * gp_index(t) - t) / 12.0


def market_rate(t):
    return market().rate(t, competitor_tenor(t))


def renewal_quote(t):
    tenor = 1.0 if renewal_architecture() == Renewal.annual_redeclare else 5.0
    return market().rate(t, tenor)


def renewal_crediting_spread(t):
    return market().spread(t)


def mva_ref_yield(t):
    return market().rate(t, mva_term(t))


def mva_fixing_yield(t):
    return market().rate(t, 5.0)


def credit_rate(t):
    if t < 12 * guar_period():
        return declared_rate_initial()
    start = redeclare_month(t)
    return max(gmir(), renewal_quote(start) - renewal_crediting_spread(start))


def mva_ref_yield_locked(t):
    if gp_index(t) <= 1:
        return mva_ref_yield_at_issue()
    return mva_fixing_yield(gp_start_month(t))


def policy_state(t):
    previous = t - 1
    year_start = t // 12 * 12
    interest = interest_credited_pp(previous) if t else 0.0
    previous_year_interest = interest_credited_pp(year_start - 1) if year_start else 0.0
    return (av_pp_at(t, AvTiming.BEF_WD), mgsv_pp(previous) if t else mgsv_pp_init(),
            pols_if(t), interest, interest - previous_year_interest,
            prem_accum_gmir_pp(previous) if t else premium_pp(),
            free_wd_avail(t), credit_rate(t), mva_ref_yield_locked(t))


def net_cf(t):
    return contract_net_cf(t) if 0 <= t < proj_len() else 0.0


def install(space, sources, overrides=None):
    """Install the canonical formulas with the DV01 market and optional restart boundaries."""
    adapters = {'market_rate': market_rate, 'competitor_tenor': competitor_tenor,
                'renewal_quote': renewal_quote,
                'renewal_crediting_spread': renewal_crediting_spread,
                'mva_ref_yield': mva_ref_yield, 'mva_fixing_yield': mva_fixing_yield,
                'credit_rate': credit_rate, 'mva_ref_yield_locked': mva_ref_yield_locked,
                'policy_state': policy_state, 'net_cf': net_cf}
    formulas = {**sources, 'contract_net_cf': sources['net_cf'], **adapters}
    formulas.update(overrides or {})
    for name, formula in formulas.items():
        space.new_cells(name, formula)
