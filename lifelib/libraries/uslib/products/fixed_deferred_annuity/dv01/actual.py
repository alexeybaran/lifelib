"""Connect the saved MYGA projection to DV01's Actual market and snapshots."""


def policy_ids():
    return tuple(sorted(int(p) for p in data.model_point_table().index))


def market(t):
    return Market(t, scen_id, -1)


def initial_state():
    return policy_state(0)


def competitor_tenor(t):
    term = 12 * guar_period()
    if renewal_architecture() == Renewal.annual_redeclare and t >= term:
        return 12
    return term * gp_index(t) - t


def market_rate(t):
    return market(t).rate(competitor_tenor(t), t)


def renewal_quote(t):
    tenor = 12 if renewal_architecture() == Renewal.annual_redeclare else 60
    return market(t).rate(tenor, t)


def renewal_crediting_spread(t):
    return renewal_spread


def mva_ref_yield(t):
    return market(t).rate(int(round(12 * mva_term(t))), t)


def mva_fixing_yield(t):
    return market(t).rate(60, t)


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
