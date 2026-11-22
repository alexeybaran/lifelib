"""Connect the saved MYGA projection to DV01's Actual market and snapshots."""


def actual_point(policy_id):
    return {'refs': {'point_id': policy_id}}


def competitor_rate(t):
    term = 12 * guar_period()
    if renewal_architecture() == Renewal.annual_redeclare and t >= term:
        tenor = 1.0
    else:
        tenor = (term * gp_index(t) - t) / 12.0
    return market().rate(t, tenor)


def renewal_quote(t):
    tenor = 1.0 if renewal_architecture() == Renewal.annual_redeclare else 5.0
    return market().rate(t, tenor)


def renewal_crediting_spread(t):
    return market().spread(t)


def mva_current_yield(t):
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


def contract_history(t, name):
    """Read canonical historical stocks and the rates booked at opening."""
    if name == 'av':
        return av_pp(t)
    if name == 'mgsv':
        return mgsv_pp(t)
    if name == 'interest':
        return interest_credited_pp(t)
    if name == 'gmir_premium':
        return prem_accum_gmir_pp(t)
    if name == 'in_force':
        return pols_if(t)
    if name == 'remaining_allowance':
        return free_wd_remain(t)
    if name == 'tax_basis':
        return tax_basis_pp(t)
    if name == 'booked_credit':
        return credit_rate(t)
    if name == 'booked_mva':
        return mva_ref_yield_locked(t)
    raise ValueError('unknown contract history')


def install(space, data, sources, refs):
    """Use the saved policy calculations with Actual-specific market boundaries."""
    space.data = data
    for name, value in refs.items():
        setattr(space, name, value)
    adapters = {'market_rate': competitor_rate, 'renewal_quote': renewal_quote,
                'renewal_crediting_spread': renewal_crediting_spread,
                'mva_ref_yield': mva_current_yield, 'mva_fixing_yield': mva_fixing_yield,
                'credit_rate': credit_rate, 'mva_ref_yield_locked': mva_ref_yield_locked,
                'policy_state': policy_state, 'net_cf': net_cf, 'contract_history': contract_history}
    space.new_cells('contract_net_cf', sources['net_cf'])
    for formulas in (sources, adapters):
        for name, formula in formulas.items():
            if name in space.cells:
                space.cells[name].formula = formula
            else:
                space.new_cells(name, formula)
