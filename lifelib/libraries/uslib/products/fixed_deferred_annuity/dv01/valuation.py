"""Canonical policy-month valuation with observed history and a local market."""

from . import actual


def contract_point(valuation_month, policy_id, shock=-1):
    return {'refs': {'point_id': policy_id}}


def market_rate(t):
    if t < valuation_month:
        return Actual[policy_id].market_rate(t)
    return market().rate(t - valuation_month, competitor_tenor(t))


def renewal_quote(t):
    if t < valuation_month:
        return Actual[policy_id].renewal_quote(t)
    tenor = 1.0 if renewal_architecture() == Renewal.annual_redeclare else 5.0
    return market().rate(t - valuation_month, tenor)


def renewal_crediting_spread(t):
    if t < valuation_month:
        return Actual[policy_id].renewal_crediting_spread(t)
    return market().spread(t - valuation_month)


def mva_ref_yield(t):
    if t < valuation_month:
        return Actual[policy_id].mva_ref_yield(t)
    return market().rate(t - valuation_month, mva_term(t))


def mva_fixing_yield(t):
    if t < valuation_month:
        return Actual[policy_id].mva_fixing_yield(t)
    return market().rate(t - valuation_month, 5.0)


def credit_rate(t):
    if t < 12 * guar_period():
        return declared_rate_initial()
    start = redeclare_month(t)
    if start <= valuation_month:
        return Actual[policy_id].credit_rate(min(t, valuation_month))
    return max(gmir(), renewal_quote(start) - renewal_crediting_spread(start))


def mva_ref_yield_locked(t):
    if gp_index(t) <= 1:
        return mva_ref_yield_at_issue()
    start = gp_start_month(t)
    if start <= valuation_month:
        return Actual[policy_id].mva_ref_yield_locked(min(t, valuation_month))
    return mva_fixing_yield(start)


def net_cf(t):
    """Net cash flow in absolute policy month t."""
    if t < valuation_month:
        return Actual[policy_id].net_cf(t)
    return contract_net_cf(t) if t < proj_len() else 0.0


def cashflow_at_offset(k):
    """Net cash flow k months after the valuation cut."""
    return net_cf(valuation_month + k) if 0 <= k < HORIZON else 0.0


def state_at_offset(k):
    """Opening policy state k months after the valuation cut."""
    return policy_state(valuation_month + k)


def discount_factor(k):
    return market().discount_factor(k)


def pv(k):
    if k >= HORIZON:
        return 0.0
    return cashflow_at_offset(k) * discount_factor(k) + pv(k + 1)


def liability_pv():
    return -pv(0)


def install(space, sources):
    overrides = {
        'market_rate': market_rate,
        'renewal_quote': renewal_quote,
        'renewal_crediting_spread': renewal_crediting_spread,
        'mva_ref_yield': mva_ref_yield,
        'mva_fixing_yield': mva_fixing_yield,
        'credit_rate': credit_rate,
        'mva_ref_yield_locked': mva_ref_yield_locked,
        'net_cf': net_cf,
        'cashflow_at_offset': cashflow_at_offset,
        'state_at_offset': state_at_offset,
        'discount_factor': discount_factor,
        'pv': pv,
        'liability_pv': liability_pv,
    }
    # Closing stocks belong to Actual before the cut. The cut's opening count
    # also belongs to Actual. Saved formulas advance the stocks from there.
    boundaries = ('av_pp', 'mgsv_pp', 'interest_credited_pp', 'prem_accum_gmir_pp',
                  'free_wd_remain', 'tax_basis_pp', 'pols_if')
    for name in boundaries:
        rollforward = f'{name}_rollforward'
        overrides[rollforward] = sources[name]
        comparison = '<=' if name == 'pols_if' else '<'
        overrides[name] = (f'lambda t: Actual[policy_id].{name}(t) '
                           f'if t {comparison} valuation_month else {rollforward}(t)')
    actual.install(space, sources, overrides)
