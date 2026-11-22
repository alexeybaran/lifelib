"""Canonical policy-month valuation with observed history and a local market."""

def market():
    return Market(valuation_month, scen_id, shock)


def initial_state():
    return Actual[policy_id, scen_id].policy_state(valuation_month)


def market_rate(t):
    if t < valuation_month:
        return Actual[policy_id, scen_id].market_rate(t)
    return market().rate(competitor_tenor(t), t)


def renewal_quote(t):
    if t < valuation_month:
        return Actual[policy_id, scen_id].renewal_quote(t)
    tenor = 12 if renewal_architecture() == Renewal.annual_redeclare else 60
    return market().rate(tenor, t)


def renewal_crediting_spread(t):
    if t < valuation_month:
        return Actual[policy_id, scen_id].renewal_crediting_spread(t)
    return renewal_spread


def mva_ref_yield(t):
    if t < valuation_month:
        return Actual[policy_id, scen_id].mva_ref_yield(t)
    return market().rate(int(round(12 * mva_term(t))), t)


def mva_fixing_yield(t):
    if t < valuation_month:
        return Actual[policy_id, scen_id].mva_fixing_yield(t)
    return market().rate(60, t)


def credit_rate(t):
    if t < 12 * guar_period():
        return declared_rate_initial()
    start = redeclare_month(t)
    if start <= valuation_month:
        return Actual[policy_id, scen_id].credit_rate(min(t, valuation_month))
    return max(gmir(), renewal_quote(start) - renewal_crediting_spread(start))


def mva_ref_yield_locked(t):
    if gp_index(t) <= 1:
        return mva_ref_yield_at_issue()
    start = gp_start_month(t)
    if start <= valuation_month:
        return Actual[policy_id, scen_id].mva_ref_yield_locked(min(t, valuation_month))
    return mva_fixing_yield(start)


def net_cf(t):
    """Net cash flow in absolute policy month t."""
    if t < valuation_month:
        return Actual[policy_id, scen_id].net_cf(t)
    return contract_net_cf(t) if t < proj_len() else 0.0


def cashflow_at_offset(k):
    """Net cash flow k months after the valuation cut."""
    return net_cf(valuation_month + k) if 0 <= k < HORIZON else 0.0


def state_at_offset(k):
    """Opening policy state k months after the valuation cut."""
    return policy_state(valuation_month + k)


def discount_factor(k):
    return market().price(valuation_month + k + 1)


def pv(k):
    if k >= HORIZON:
        return 0.0
    return cashflow_at_offset(k) * discount_factor(k) + pv(k + 1)


def liability_pv():
    return -pv(0)


# Closing stocks come from Actual before the cut. The cut's opening in-force
# count also comes from Actual. Canonical MYGA rollforwards advance them.
def av_pp(t):
    return Actual[policy_id, scen_id].av_pp(t) if t < valuation_month else av_pp_rollforward(t)


def mgsv_pp(t):
    return Actual[policy_id, scen_id].mgsv_pp(t) if t < valuation_month else mgsv_pp_rollforward(t)


def interest_credited_pp(t):
    if t < valuation_month:
        return Actual[policy_id, scen_id].interest_credited_pp(t)
    return interest_credited_pp_rollforward(t)


def prem_accum_gmir_pp(t):
    if t < valuation_month:
        return Actual[policy_id, scen_id].prem_accum_gmir_pp(t)
    return prem_accum_gmir_pp_rollforward(t)


def free_wd_remain(t):
    return Actual[policy_id, scen_id].free_wd_remain(t) if t < valuation_month else free_wd_remain_rollforward(t)


def tax_basis_pp(t):
    return Actual[policy_id, scen_id].tax_basis_pp(t) if t < valuation_month else tax_basis_pp_rollforward(t)


def pols_if(t):
    return Actual[policy_id, scen_id].pols_if(t) if t <= valuation_month else pols_if_rollforward(t)
