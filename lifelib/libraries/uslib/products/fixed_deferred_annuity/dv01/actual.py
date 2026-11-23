"""Connect the saved MYGA projection to DV01's Actual market and snapshots."""


def policy_ids():
    return tuple(sorted(int(p) for p in data.model_point_table().index))


def history_months():
    return range(max(last_snapshot_month, through_month) + 1)


def opening_months():
    return range(max(last_snapshot_month, through_month) + 2)


def market(t):
    return Market(t, scen_id, -1)


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
    return market(t).rate(round(12 * mva_term(t)), t)


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


def opening_account_value(t):
    return av_pp_at(t, AvTiming.BEF_WD)


def opening_guaranteed_surrender_value(t):
    return mgsv_pp(t - 1) if t else mgsv_pp_init()


def interest_credited_to_date(t):
    return interest_credited_pp(t - 1) if t else 0.0


def interest_credited_policy_year_to_date(t):
    return interest_credited_to_date(t) - interest_credited_to_date(t // 12 * 12)


def opening_accumulated_guaranteed_premiums(t):
    return prem_accum_gmir_pp(t - 1) if t else premium_pp()


def net_cf(t):
    return contract_net_cf(t) if 0 <= t < proj_len() else 0.0
