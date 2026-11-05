"""Ordinary single-policy MYGA modelx formulas.

Arithmetic and actuarial rules are retained from the supplied Iteration-8
assembly. Policy assumptions are calculated by Cells, not prepared month arrays. Policy identity is an ordinary Dynamic Space argument. `state` and `Market` are dynamic References; shared tables are held by Data. Time t is relative
to the invocation's valuation_month, as in the baseline valuation formulas.
No formula is written in compiler-specific syntax.
"""

def idx(t):
    return t


def state_value(k):
    return initial_state[k]


def credit_rate(t):
    if t == 0:
        return state_value(7)
    j = idx(t)
    if redeclare(t) > 0.5:
        return max(gmir(), declaration_yield(t) - spread)
    return credit_rate(t - 1)


def mva_ref_locked(t):
    if t == 0:
        return state_value(8)
    j = idx(t)
    if redeclare(t) > 0.5:
        return mva_lock_yield(t)
    return mva_ref_locked(t - 1)


def credit_rate_mth(t):
    return (1.0 + credit_rate(t)) ** (1.0 / 12.0) - 1.0


def av_open(t):
    if t == 0:
        return state_value(0)
    return av_eom(t - 1)


def free_wd_avail(t):
    if t == 0:
        return state_value(6)
    j = idx(t)
    if anniversary(t) > 0.5:
        if free_rule() < 0.5:
            return free_rate() * av_open(t)
        return interest_ytd_eom(t - 1)
    return free_wd_remain(t - 1)


def wd_pp(t):
    return wd(t)


def wd_free_pp(t):
    return min(wd_pp(t), free_wd_avail(t))


def free_wd_remain(t):
    return free_wd_avail(t) - wd_free_pp(t)


def wd_excess_pp(t):
    if free_exempt() > 0.5:
        return max(0.0, wd_pp(t) - free_wd_avail(t))
    return wd_pp(t)


def av_bef_inv(t):
    return av_open(t) - wd_pp(t)


def av_eom(t):
    return av_bef_inv(t) * (1.0 + credit_rate_mth(t))


def interest_month(t):
    return av_bef_inv(t) * credit_rate_mth(t)


def interest_cum_open(t):
    if t == 0:
        return state_value(3)
    return interest_cum_eom(t - 1)


def interest_cum_eom(t):
    return interest_cum_open(t) + interest_month(t)


def interest_ytd_open(t):
    if t == 0:
        return state_value(4)
    if anniversary(t) > 0.5:
        return 0.0
    return interest_ytd_eom(t - 1)


def interest_ytd_eom(t):
    return interest_ytd_open(t) + interest_month(t)


def prem_gmir_open(t):
    if t == 0:
        return state_value(5)
    return prem_gmir_eom(t - 1)


def prem_gmir_eom(t):
    return (prem_gmir_open(t) - wd_pp(t)) * (1.0 + gmir()) ** (1.0 / 12.0)


def mva_in_force(t):
    j = idx(t)
    return mva_term(t) > 0.0 and gp_window(t) < 0.5


def surr_excess_pp(t):
    if free_exempt() > 0.5:
        return max(0.0, av_eom(t) - free_wd_remain(t))
    return av_eom(t)


def surr_charge_pp(t):
    return surr_charge(t) * surr_excess_pp(t)


def wd_charge_pp(t):
    return surr_charge(t) * wd_excess_pp(t)


def mva_rate(t):
    if not mva_in_force(t):
        return 0.0
    j = idx(t)
    family = mva_family()
    if family < 0.5:
        return (mva_ref_locked(t) - mva_ref_yield(t)) * mva_term(t)
    if family < 1.5:
        return ((1.0 + mva_ref_locked(t)) / (1.0 + mva_ref_yield(t) + mva_admin_spread)) ** mva_term(t) - 1.0
    factor = mva_factor_lo(t)
    if credit_rate(t) >= 0.06:
        factor = mva_factor_hi(t)
    return (credit_rate(t) - market_rate(t)) * factor


def mva_amount(t, is_wd):
    if is_wd == 1:
        base = wd_excess_pp(t)
    else:
        base = surr_excess_pp(t)
    raw = mva_rate(t) * base
    rule = mva_cap()
    if rule > 3.5:
        return raw
    charge = surr_charge(t) * base
    if rule < 0.5:
        return max(-charge, min(charge, raw))
    if rule < 1.5:
        limit = min(charge, interest_cum_eom(t))
        return max(-limit, min(limit, raw))
    if rule < 2.5:
        return min(charge, raw)
    return max(raw, prem_gmir_eom(t) - av_eom(t))


def mva_pp(t):
    return mva_amount(t, 0)


def wd_mva_pp(t):
    return mva_amount(t, 1)


def wd_payment_pp(t):
    return wd_pp(t) + wd_mva_pp(t) - wd_charge_pp(t)


def mgsv_open(t):
    if t == 0:
        return state_value(1)
    return mgsv_eom(t - 1)


def mgsv_wd_deduct(t):
    if mgsv_net_wd() > 0.5:
        return wd_payment_pp(t)
    return wd_pp(t)


def mgsv_eom(t):
    return (mgsv_open(t) - mgsv_wd_deduct(t) - mgsv_charge() / 12.0) * (1.0 + mgsv_rate()) ** (1.0 / 12.0)


def surr_value_pp(t):
    return av_eom(t) + mva_pp(t) - surr_charge_pp(t)


def surr_benefit_pp(t):
    return max(surr_value_pp(t), mgsv_eom(t))


def lapse_dyn_market(t):
    cr = credit_rate(t)
    mr = market_rate(t)
    power = lapse_power(t)
    if cr >= mr:
        return -1.25 * (cr - mr) ** power
    if cr >= mr - 0.005:
        return 0.0
    return 1.25 * (mr - 0.005 - cr) ** power


def lapse_dyn_rate(t):
    return lapse_dyn_market(t) * max(0.0, 1.0 - 5.0 * (1.0 - surr_benefit_pp(t) / av_eom(t)))


def lapse_rate(t):
    dyn_factor = 0.35 if mva_in_force(t) else 1.0
    rate = lapse_base(t) * 1.25 + lapse_dyn_rate(t) * dyn_factor
    return min(0.9, max(0.005, rate))


def lapse_rate_mth(t):
    return 1.0 - (1.0 - lapse_rate(t)) ** (1.0 / 12.0)


def ann_rate(t):
    return 0.01 if gp_window(t) > 0.5 else 0.0


def pols_open(t):
    if t == 0:
        return state_value(2)
    return pols_eom(t - 1)


def pols_after_ann(t):
    return pols_open(t) * (1.0 - ann_rate(t))


def pols_after_mort(t):
    return pols_after_ann(t) * (1.0 - mort(t))


def pols_after_lapse(t):
    return pols_after_mort(t) * (1.0 - lapse_rate_mth(t))


def pols_eom(t):
    return pols_after_lapse(t) * (1.0 - maturity(t))


def pols_ann(t):
    return pols_open(t) * ann_rate(t)


def pols_death(t):
    return pols_after_ann(t) * mort(t)


def pols_lapse(t):
    return pols_after_mort(t) * lapse_rate_mth(t)


def pols_maturity(t):
    return pols_after_lapse(t) * maturity(t)


def claims(t):
    death = max(av_eom(t), surr_benefit_pp(t)) * pols_death(t)
    lapse = surr_benefit_pp(t) * pols_lapse(t)
    ann = av_bef_inv(t) * pols_ann(t)
    maturity = max(av_eom(t), mgsv_eom(t)) * pols_maturity(t)
    return death + lapse + ann + maturity


def withdrawal_cf(t):
    return wd_payment_pp(t) * pols_open(t)


def commission_cf(t):
    return 0.02 * premium(t)


def premium_tax_cf(t):
    return premium_tax() * premium(t)


def expense_cf(t):
    return 50.0 / 12.0 * inflation(t) * pols_open(t)


def net_cf(t):
    return premium(t) - withdrawal_cf(t) - claims(t) - commission_cf(t) - premium_tax_cf(t) - expense_cf(t)


def pv(t):
    if t >= HORIZON:
        return 0.0
    return net_cf(t) * discount_factor(t) + pv(t + 1)


def liability_pv():
    return -pv(0)


def av(t):
    return av_open(t)


def policy_state(t):
    return np.array([
        av_open(t), mgsv_open(t), pols_open(t), interest_cum_open(t),
        interest_ytd_open(t), prem_gmir_open(t), free_wd_avail(t),
        credit_rate(t), mva_ref_locked(t),
    ], dtype=float)
