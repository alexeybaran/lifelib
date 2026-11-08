from enum import IntEnum


class Sex(IntEnum):
    M = 0
    F = 1


class Renewal(IntEnum):
    rollover = 0
    annual_redeclare = 1


class FreeRule(IntEnum):
    pct_av = 0
    interest_only = 1


class MgsvWithdrawal(IntEnum):
    gross = 0
    net_of_charges = 1


class MvaFamily(IntEnum):
    linear_duration = 0
    geometric = 1
    declared_differential = 2


class Cap(IntEnum):
    none = 0
    sym_sc = 1
    min_sc_interest = 2
    asym_sc_snfl = 3
    gmir_floor = 4


class Schedule(IntEnum):
    initial = 0
    renewal = 1
    none = 2


class AvTiming(IntEnum):
    BEF_WD = 0
    BEF_INV = 1
    EOM = 2


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_MORT = 1
    BEF_LAPSE = 2
    AFT_DECR = 3


class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    ANNUITIZATION = 2
    MATURITY = 3
    ALL = 4


class RateColumn(IntEnum):
    mva_ref_yield = 0
    market_rate = 1


class FactorColumn(IntEnum):
    factor_lo = 0
    factor_hi = 1


def model_point():
    return policy_rows[point_id]


def guar_period_months():
    return 12 * guar_period()


def attained_age(completed_years):
    return age_at_entry() + completed_years


def age(t):
    return attained_age(duration(t))


def gp_index(t):
    return t // guar_period_months() + 1


def gp_start_month(t):
    return guar_period_months() * (gp_index(t) - 1)


def gp_end(t):
    return guar_period_months() * gp_index(t) - (t + 1)


def in_gp_window(t):
    n12 = guar_period_months()
    if t <= 0 or t % n12 != 0:
        return False
    if renewal_architecture() == Renewal.annual_redeclare:
        return t == n12
    return True


def redeclare_month(t):
    n12 = guar_period_months()
    if t < n12:
        return 0
    if renewal_architecture() == Renewal.rollover:
        return n12 * (gp_index(t) - 1)
    return 12 * duration(t)


def scenario_rate(t, name):
    return previous(scenario_table(), t, name)


def scenario_table():
    return subtable(rate_scenario, scenario_id())


def market_rate(t):
    return scenario_rate(t, RateColumn.market_rate)


def mva_ref_yield(t):
    return scenario_rate(t, RateColumn.mva_ref_yield)


def credit_rate(t):
    if t < guar_period_months():
        return declared_rate_initial()
    return max(gmir(), market_rate(redeclare_month(t)) - renewal_spread)


def has_withdrawal_schedule():
    return has_group(withdrawal_table, wd_schedule_id())


def withdrawal_schedule():
    return subtable(withdrawal_table, wd_schedule_id())


def wd_scheduled_pp(t):
    if not has_withdrawal_schedule():
        return 0.0
    return lookup(withdrawal_schedule(), t, 'wd_amount', 0.0)


def av_pp(t):
    return av_pp_at(t, AvTiming.BEF_INV) * (1.0 + credit_rate_mth(t))


def av_pp_at(t, timing):
    if timing == AvTiming.BEF_WD:
        return av_pp_init() if t == 0 else av_pp(t - 1)
    elif timing == AvTiming.BEF_INV:
        return av_pp_at(t, AvTiming.BEF_WD) - wd_pp(t)
    elif timing == AvTiming.EOM:
        return av_pp(t)
    else:
        raise ValueError('invalid timing')


def inv_income_pp(t):
    return av_pp_at(t, AvTiming.BEF_INV) * credit_rate_mth(t)


def free_wd_base(y):
    return premium_pp() if y <= 1 else av_pp_at(12 * (y - 1), AvTiming.BEF_WD)


def free_wd_allow(y):
    rule = free_wd_rule()
    if rule == FreeRule.pct_av:
        return free_wd_rate() * free_wd_base(y)
    elif rule == FreeRule.interest_only:
        if y <= 1:
            return 0.0
        prior = interest_credited_pp(12 * (y - 2) - 1) if y > 2 else 0.0
        return interest_credited_pp(12 * (y - 1) - 1) - prior
    else:
        raise ValueError('invalid free_wd_rule')


def surr_charge_id(t):
    if gp_index(t) <= 1:
        return Schedule.initial
    if renewal_architecture() == Renewal.annual_redeclare:
        return Schedule.none
    return Schedule.renewal


def surr_charge_age_cap(t):
    attained = age(t)
    lo = first_key(surr_charge_age_cap_table)
    hi = last_key(surr_charge_age_cap_table)
    if attained < lo:
        return 1.0
    return lookup(surr_charge_age_cap_table, min(attained, hi), 'surr_charge_cap')


def surr_charge_rate(t):
    schedule = surr_charge_id(t)
    if schedule == Schedule.none or in_gp_window(t):
        return 0.0
    if not has_group(surr_charge_table, schedule):
        return 0.0
    key = surr_charge_year(t)
    table = subtable(surr_charge_table, schedule)
    if not contains(table, key):
        return 0.0
    return min(lookup(table, key, 'surr_charge_rate'), surr_charge_age_cap(t))


def mva_term(t):
    if renewal_architecture() == Renewal.annual_redeclare and t >= guar_period_months():
        return 0.0
    months_to_year_end = 12 * policy_year(t) - (t + 1)
    whole_years_left = guar_period() * gp_index(t) - policy_year(t)
    return months_to_year_end / 12.0 + whole_years_left


def mva_duration_factor(t):
    column = FactorColumn.factor_lo if credit_rate(t) < mva_factor_rate_split else FactorColumn.factor_hi
    years = mva_term(t)
    prepared = prepared_interpolation(mva_factor_table, column, years, lookup, last_key, math)
    if prepared is not None:
        return prepared
    last = last_key(mva_factor_table)
    lower = int(math.floor(years))
    if lower >= last:
        return lookup(mva_factor_table, last, column)
    f0 = lookup(mva_factor_table, lower, column)
    f1 = lookup(mva_factor_table, lower + 1, column)
    return f0 + (f1 - f0) * (years - lower)


def mva_rate(t):
    if not mva_in_force(t):
        return 0.0
    family = mva_family()
    if family == MvaFamily.linear_duration:
        return (mva_ref_yield_locked(t) - mva_ref_yield(t)) * mva_term(t)
    elif family == MvaFamily.geometric:
        return mva_factor_geometric(mva_ref_yield_locked(t), mva_ref_yield(t), mva_term(t)) - 1.0
    elif family == MvaFamily.declared_differential:
        return (credit_rate(t) - market_rate(t)) * mva_duration_factor(t)
    else:
        raise ValueError('invalid mva_family')


def mva_pp_on(t, base):
    raw = mva_rate(t) * base
    rule = mva_cap_rule()
    if rule == Cap.none:
        return raw
    charge = surr_charge_rate(t) * base
    if rule == Cap.sym_sc:
        return max(-charge, min(charge, raw))
    elif rule == Cap.min_sc_interest:
        limit = min(charge, interest_credited_pp(t))
        return max(-limit, min(limit, raw))
    elif rule == Cap.asym_sc_snfl:
        return min(charge, raw)
    elif rule == Cap.gmir_floor:
        return max(raw, prem_accum_gmir_pp(t) - av_pp(t))
    else:
        raise ValueError('invalid mva_cap_rule')


def mgsv_wd_deduct_pp(t):
    convention = mgsv_wd_convention()
    if convention == MgsvWithdrawal.gross:
        return wd_pp(t)
    elif convention == MgsvWithdrawal.net_of_charges:
        return wd_payment_pp(t)
    else:
        raise ValueError('invalid mgsv_wd_convention')


def taxable_wd_pp(t):
    opening_basis = tax_basis_pp_init() if t == 0 else tax_basis_pp(t - 1)
    gain = max(0.0, av_pp_at(t, AvTiming.BEF_WD) - opening_basis)
    return min(wd_pp(t), gain)


def mortality_schedule():
    return subtable(mort_table, sex())


def mort_rate_for_year(completed_years):
    return lookup(mortality_schedule(), attained_age(completed_years), 'mort_rate')


def mort_rate(t):
    return mort_rate_for_year(duration(t))


def mort_rate_mth_for_year(completed_years):
    return 1.0 - (1.0 - mort_rate_for_year(completed_years)) ** (1.0 / 12.0)


def mort_rate_mth(t):
    return mort_rate_mth_for_year(duration(t))


def lapse_rate_base(t):
    year = policy_year(t)
    n = guar_period()
    if renewal_architecture() == Renewal.rollover:
        if year > n and (year - 1) % n == 0:
            return lapse_base_shock
        return lapse_base_igp
    if year <= n:
        return lapse_base_igp
    elif year == n + 1:
        return lapse_base_shock
    elif year == n + 2:
        return lapse_base_post1
    elif year == n + 3:
        return lapse_base_post2
    else:
        return lapse_base_ult


def pols_if(t):
    if t == 0:
        return pols_if_init()
    if t >= proj_len():
        return 0.0
    return pols_if_at(t - 1, PolTiming.AFT_DECR)


def pols_if_at(t, timing):
    pols = pols_if(t)
    if timing == PolTiming.BEF_DECR:
        return pols
    pols = pols * (1.0 - annuitization_rate(t))
    if timing == PolTiming.BEF_MORT:
        return pols
    pols = pols * (1.0 - mort_rate_mth(t))
    if timing == PolTiming.BEF_LAPSE:
        return pols
    pols = pols * (1.0 - lapse_rate_mth(t))
    if timing == PolTiming.AFT_DECR:
        return pols
    raise ValueError('invalid timing')


def pols_annuitization(t):
    return pols_if_at(t, PolTiming.BEF_DECR) * annuitization_rate(t)


def pols_death(t):
    return pols_if_at(t, PolTiming.BEF_MORT) * mort_rate_mth(t)


def pols_lapse(t):
    return pols_if_at(t, PolTiming.BEF_LAPSE) * lapse_rate_mth(t)


def pols_maturity(t):
    return pols_if_at(t, PolTiming.AFT_DECR) if t == proj_len() - 1 else 0.0


def pols_decr(t, kind):
    if kind == Kind.DEATH:
        return pols_death(t)
    elif kind == Kind.LAPSE:
        return pols_lapse(t)
    elif kind == Kind.ANNUITIZATION:
        return pols_annuitization(t)
    elif kind == Kind.MATURITY:
        return pols_maturity(t)
    else:
        raise ValueError('invalid kind')


def annuitization_pp(t):
    account = av_pp_at(t, AvTiming.BEF_INV)
    if in_gp_window(t):
        return account
    excess = max(0.0, account - free_wd_remain(t)) if free_wd_mva_exempt() else account
    return account - surr_charge_rate(t) * excess


def claim_pp(t, kind):
    if kind == Kind.DEATH:
        return max(av_pp(t), surr_benefit_pp(t))
    elif kind == Kind.LAPSE:
        return surr_benefit_pp(t)
    elif kind == Kind.ANNUITIZATION:
        return annuitization_pp(t)
    elif kind == Kind.MATURITY:
        return max(av_pp(t), mgsv_pp(t))
    else:
        raise ValueError('invalid kind')


def claim_from_av_pp(t, kind):
    if kind == Kind.ANNUITIZATION:
        return av_pp_at(t, AvTiming.BEF_INV)
    elif kind in (Kind.DEATH, Kind.LAPSE, Kind.MATURITY):
        return av_pp(t)
    else:
        raise ValueError('invalid kind')


def claims(t, kind=4):
    if kind == Kind.ALL:
        return claims(t, Kind.DEATH) + claims(t, Kind.LAPSE) + claims(t, Kind.ANNUITIZATION) + claims(t, Kind.MATURITY)
    return claim_pp(t, kind) * pols_decr(t, kind)


def claims_over_av(t, kind=4):
    if kind == Kind.ALL:
        return claims_over_av(t, Kind.DEATH) + claims_over_av(t, Kind.LAPSE) + claims_over_av(t, Kind.ANNUITIZATION) + claims_over_av(t, Kind.MATURITY)
    return claims(t, kind) - claims_from_av(t, kind)


def av_at(t, timing):
    if timing == AvTiming.BEF_WD:
        return av_pp_at(t, AvTiming.BEF_WD) * pols_if(t)
    elif timing == AvTiming.BEF_INV:
        return av_pp_at(t, AvTiming.BEF_INV) * pols_if_at(t, PolTiming.BEF_MORT)
    elif timing == AvTiming.EOM:
        return av_pp(t) * pols_if(t + 1)
    else:
        raise ValueError('invalid timing')


def inv_income(t):
    return av_at(t, AvTiming.BEF_INV) * credit_rate_mth(t)


def av_change(t):
    opening = av_at(t - 1, AvTiming.EOM) if t > 0 else 0.0
    return av_at(t, AvTiming.EOM) - opening


def check_pols_roll_fwd():
    return all_true(abs(check_pols_roll_fwd_resid(t)) <= check_tol_pols for t in range(proj_len()))


def check_av_roll_fwd():
    return all_true(abs(check_av_roll_fwd_resid(t)) <= check_tol_av for t in range(proj_len()))


def check_av_roll_fwd_resid(t):
    expected = prem_to_av(t) - wd_from_av(t) + inv_income(t) - claims_from_av(t, Kind.ANNUITIZATION) - claims_from_av(t, Kind.DEATH) - claims_from_av(t, Kind.LAPSE) - claims_from_av(t, Kind.MATURITY)
    return av_change(t) - expected


def result_cf():
    ts = list(range(proj_len()))
    return pd.DataFrame(                                             # noqa: F821
        {
            "pols_if": [pols_if(t) for t in ts],
            "premiums": [premiums(t) for t in ts],
            "withdrawals": [withdrawals(t) for t in ts],
            "claims_death": [claims(t, Kind.DEATH) for t in ts],
            "claims_lapse": [claims(t, Kind.LAPSE) for t in ts],
            "claims_annuitization": [claims(t, Kind.ANNUITIZATION) for t in ts],
            "claims_maturity": [claims(t, Kind.MATURITY) for t in ts],
            "commissions": [commissions(t) for t in ts],
            "expenses": [expenses(t) for t in ts],
            "premium_taxes": [premium_taxes(t) for t in ts],
            "net_cf": [net_cf(t) for t in ts],
        },
        index=pd.Index(ts, name="t"),                                # noqa: F821
    )


def result_pols():
    ts = list(range(proj_len()))
    return pd.DataFrame(                                             # noqa: F821
        {
            "pols_if": [pols_if(t) for t in ts],
            "pols_annuitization": [pols_annuitization(t) for t in ts],
            "pols_death": [pols_death(t) for t in ts],
            "pols_lapse": [pols_lapse(t) for t in ts],
            "pols_maturity": [pols_maturity(t) for t in ts],
            "pols_if_aft_decr": [pols_if_at(t, PolTiming.AFT_DECR) for t in ts],
        },
        index=pd.Index(ts, name="t"),                                # noqa: F821
    )


def result_av():
    ts = list(range(proj_len()))
    return pd.DataFrame(                                             # noqa: F821
        {
            "av_pp_bef_wd": [av_pp_at(t, AvTiming.BEF_WD) for t in ts],
            "wd_pp": [wd_pp(t) for t in ts],
            "av_pp_bef_inv": [av_pp_at(t, AvTiming.BEF_INV) for t in ts],
            "av_pp": [av_pp(t) for t in ts],
            "mgsv_pp": [mgsv_pp(t) for t in ts],
            "free_wd_avail": [free_wd_remain(t) for t in ts],
            "surr_charge_pp": [surr_charge_pp(t) for t in ts],
            "mva_pp": [mva_pp(t) for t in ts],
            "surr_value_pp": [surr_value_pp(t) for t in ts],
            "surr_benefit_pp": [surr_benefit_pp(t) for t in ts],
        },
        index=pd.Index(ts, name="t"),                                # noqa: F821
    )


CELLS = (
    'model_point',
    'guar_period_months',
    'attained_age',
    'age',
    'gp_index',
    'gp_start_month',
    'gp_end',
    'in_gp_window',
    'redeclare_month',
    'scenario_rate',
    'scenario_table',
    'market_rate',
    'mva_ref_yield',
    'credit_rate',
    'has_withdrawal_schedule',
    'withdrawal_schedule',
    'wd_scheduled_pp',
    'av_pp',
    'av_pp_at',
    'inv_income_pp',
    'free_wd_base',
    'free_wd_allow',
    'surr_charge_id',
    'surr_charge_age_cap',
    'surr_charge_rate',
    'mva_term',
    'mva_duration_factor',
    'mva_rate',
    'mva_pp_on',
    'mgsv_wd_deduct_pp',
    'taxable_wd_pp',
    'mortality_schedule',
    'mort_rate_for_year',
    'mort_rate',
    'mort_rate_mth_for_year',
    'mort_rate_mth',
    'lapse_rate_base',
    'pols_if',
    'pols_if_at',
    'pols_annuitization',
    'pols_death',
    'pols_lapse',
    'pols_maturity',
    'pols_decr',
    'annuitization_pp',
    'claim_pp',
    'claim_from_av_pp',
    'claims',
    'claims_over_av',
    'av_at',
    'inv_income',
    'av_change',
    'check_av_roll_fwd',
    'check_pols_roll_fwd',
    'check_av_roll_fwd_resid',
    'result_cf',
    'result_pols',
    'result_av',
)
