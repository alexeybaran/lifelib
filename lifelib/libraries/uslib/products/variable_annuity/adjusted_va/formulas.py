from enum import IntEnum


class StepupBasis(IntEnum):
    annual_CV = 0
    highest_quarterly_CV = 1


class GmdbOption(IntEnum):
    rollup = 0
    HQAV = 1
    basic = 2


class FeeResetRule(IntEnum):
    none = 0
    quinquennial = 1
    vix = 2


class RollupRule(IntEnum):
    fixed = 0
    cmt_linked = 1


class AvTiming(IntEnum):
    BEF_PREM = 0
    BEF_WD = 1
    BEF_INV = 2
    BEF_FEE = 3
    EOM = 4


class BenefitTiming(IntEnum):
    BEF_PREM = 0
    BEF_WD = 1
    BEF_ANNIV = 2


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
    ALL = 3


def model_point():
    return policy_rows[point_id]


def alloc(i):
    return lookup(fund_rows(), i, 'alloc')


def fund_expense_rate(i):
    return lookup(fund_rows(), i, 'fund_expense')


def inv_return_mth(t, i):
    return previous(fund_return_rows(i), max(duration_mth(t), 0), 'gross_return')


def scenario_rate(t, name):
    return previous(subtable(subtable(rate_scenarios, scenario_id()), name), max(duration_mth(t), 0), 'rate')


def sa_pp_at(t, i, timing):
    if t < 0 or t >= proj_len() or depleted_flag(t - 1):
        return 0.0
    sa = alloc(i) * av_pp_init() if t == 0 else sa_pp(t - 1, i)
    if timing == AvTiming.BEF_PREM:
        return sa
    sa = sa + alloc(i) * prem_to_av_pp(t)
    if timing == AvTiming.BEF_WD:
        return sa
    base = av_pp_at(t, AvTiming.BEF_WD)
    sa = sa * (1.0 - wd_pp(t) / base) if base > 0.0 else 0.0
    if timing == AvTiming.BEF_INV:
        return sa
    sa = sa * unit_growth(t, i)
    if timing == AvTiming.BEF_FEE:
        return sa
    base = av_pp_at(t, AvTiming.BEF_FEE)
    sa = sa * (1.0 - charge_pp(t) / base) if base > 0.0 else 0.0
    if timing == AvTiming.EOM:
        return sa
    raise ValueError('invalid timing')


def sa_pp(t, i):
    return sa_pp_at(t, i, AvTiming.EOM)


def av_pp_at(t, timing):
    return sum_f64((sa_pp_at(t, fund_id(k), timing) for k in range(fund_count())))


def av_pp(t):
    return av_pp_at(t, AvTiming.EOM)


def sa_weight(t, i):
    base = av_pp_at(t, AvTiming.BEF_FEE)
    return sa_pp_at(t, i, AvTiming.BEF_FEE) / base if base > 0.0 else 0.0


def gross_inv_income_pp(t):
    if t < 0 or depleted_flag(t - 1):
        return 0.0
    return sum_f64((sa_pp_at(t, fund, AvTiming.BEF_INV) * inv_return_mth(t, fund) for k in range(fund_count()) for fund in (fund_id(k),)))


def fund_expense_pp(t):
    if t < 0 or depleted_flag(t - 1):
        return 0.0
    return sum_f64((sa_pp_at(t, fund, AvTiming.BEF_INV) * (1.0 + inv_return_mth(t, fund)) * fund_expense_rate(fund) / 12.0 for k in range(fund_count()) for fund in (fund_id(k),)))


def asset_charge_pp(t):
    if t < 0 or depleted_flag(t - 1):
        return 0.0
    rate = (asset_charge_me + asset_charge_admin) / 12.0
    return sum_f64((sa_pp_at(t, fund, AvTiming.BEF_INV) * (1.0 + inv_return_mth(t, fund)) * (1.0 - fund_expense_rate(fund) / 12.0) * rate for k in range(fund_count()) for fund in (fund_id(k),)))


def inv_income_pp(t):
    if t < 0:
        return 0.0
    return av_pp_at(t, AvTiming.BEF_FEE) - av_pp_at(t, AvTiming.BEF_INV)


def is_wd_year(t):
    first = t_of_month(12 * (policy_year(t) - 1))
    return any_true(is_wd_taken(u) for u in range(max(0, first), min(first + 12, proj_len())))


def prem_scheduled_pp(t):
    if t < 0 or not has_transactions():
        return 0.0
    return lookup(transaction_rows(), duration_mth(t), 'prem_amount', 0.0)


def wd_scheduled_pp(t):
    if t < 0 or not has_transactions():
        return 0.0
    return lookup(transaction_rows(), duration_mth(t), 'wd_amount', 0.0)


def gawa_pct_at_age(a):
    grid = subtable(gawa_table, glwb_option())
    return previous(grid, a, 'gawa_pct', 0.0)


def wd_limit_pp(t):
    if is_first_wd(t):
        return gawa_pct_at_age(age(t)) * gwb_pp_at(t, BenefitTiming.BEF_WD)
    return gawa_pp_at(t, BenefitTiming.BEF_WD)


def wd_pp(t):
    return min(wd_pp_due(t), av_pp_at(t, AvTiming.BEF_WD))


def cv_pre_excess_pp(t):
    return av_pp_at(t, AvTiming.BEF_WD) - wd_nonexcess_pp(t)


def free_wd_allow(t):
    rp = (rp_pp_init() if t == 0 else rp_pp(t - 1)) + premium_pp(t)
    earnings = max(0.0, av_pp_at(t, AvTiming.BEF_WD) - rp)
    return max(earnings, free_wd_rate * rp)


def surr_charge_rate(t):
    grid = charge_rows()
    return lookup(grid, min(duration(t), last_key(grid)), 'surr_charge_rate')


def phi_glwb(t):
    rule = fee_reset_rule()
    if rule == FeeResetRule.none:
        return phi_glwb_curr
    elif rule == FeeResetRule.quinquennial:
        steps = duration(t) // fee_reset_years
        return min(phi_glwb_max, phi_glwb_curr + fee_increase_max * steps)
    elif rule == FeeResetRule.vix:
        return phi_glwb_vix(contract_quarter(t))
    else:
        raise ValueError('invalid fee_reset_rule')


def phi_gmdb(t):
    return 0.0 if gmdb_option() == GmdbOption.basic else phi_gmdb_curr


def rollup_rate(t):
    if rollup_rule() == RollupRule.fixed:
        return rollup_pct()
    elif rollup_rule() == RollupRule.cmt_linked:
        spread = cmt_spread if has_wd_by(t) else cmt_spread_predraw
        raw = cmt10(t) + spread
        step = cmt_round_step
        rounded = math.floor(raw / step + 0.5) * step
        return max(cmt_floor, min(cmt_cap, rounded))
    else:
        raise ValueError('invalid rollup_rule')


def fee_glwb_pp_due(t):
    if t < 0 or depleted_flag(t - 1) or (not is_quarterly_anniv(t)):
        return 0.0
    return phi_glwb(t) / 4.0 * gwb_pp_at(t, BenefitTiming.BEF_ANNIV)


def fee_gmdb_pp_due(t):
    if t < 0 or depleted_flag(t - 1) or (not is_quarterly_anniv(t)):
        return 0.0
    return phi_gmdb(t) / 4.0 * rb_pp_at(t, BenefitTiming.BEF_ANNIV)


def maint_fee_pp_due(t):
    if t < 0 or depleted_flag(t - 1) or (not is_anniv(t)):
        return 0.0
    after_riders = av_pp_at(t, AvTiming.BEF_FEE) - fee_glwb_pp_due(t) - fee_gmdb_pp_due(t)
    return 0.0 if after_riders >= maint_fee_waiver_av else maint_fee


def charge_scale(t):
    due = charge_pp_due(t)
    if due <= 0.0:
        return 0.0
    return min(1.0, av_pp_at(t, AvTiming.BEF_FEE) / due)


def gwb_pp_at(t, timing):
    g = gwb_pp_init() if t == 0 else gwb_pp(t - 1)
    if depleted_flag(t - 1):
        return g
    if timing == BenefitTiming.BEF_PREM:
        return g
    g = min(gwb_cap, g + prem_to_av_pp(t))
    if timing == BenefitTiming.BEF_WD:
        return g
    if wd_pp(t) > 0.0:
        if sum_wd_pp(t) <= wd_limit_pp(t):
            g = max(g - wd_pp(t), 0.0)
        else:
            g = max((g - wd_nonexcess_pp(t)) * excess_factor(t), 0.0)
    if timing == BenefitTiming.BEF_ANNIV:
        return g
    raise ValueError('invalid timing')


def bb_pp_bef_anniv(t):
    prev = bb_pp_init() if t == 0 else bb_pp(t - 1)
    if depleted_flag(t - 1):
        return prev
    b = min(gwb_cap, prev + prem_to_av_pp(t))
    if wd_pp(t) > 0.0 and sum_wd_pp(t) > wd_limit_pp(t):
        b = min(gwb_pp_at(t, BenefitTiming.BEF_ANNIV), b)
    return b


def gwb_pp_aft_bonus(t):
    return gwb_pp_at(t, BenefitTiming.BEF_ANNIV) + bonus_pp(t)


def stepup_base_pp(t):
    basis = stepup_basis()
    if basis == StepupBasis.annual_CV:
        return av_pp(t)
    if basis != StepupBasis.highest_quarterly_CV or t < 0:
        raise ValueError('invalid step-up basis or month')
    return max_value(av_pp(month) for month in range(t, max(-1, t - 12), -3))


def gawa_pp_at(t, timing):
    g = gawa_pp_init() if t == 0 else gawa_pp(t - 1)
    if depleted_flag(t - 1):
        return g
    if timing == BenefitTiming.BEF_PREM:
        return g
    had_wd = has_wd_init() if t == 0 else has_wd_by(t - 1)
    if had_wd and prem_to_av_pp(t) > 0.0:
        pct = gawa_pct_init() if t == 0 else gawa_pct_fixed(t - 1)
        g = g + pct * prem_to_av_pp(t)
    if timing == BenefitTiming.BEF_WD:
        return g
    if is_first_wd(t):
        g = gawa_pct_at_age(age(t)) * gwb_pp_at(t, BenefitTiming.BEF_WD)
    if wd_pp(t) > 0.0 and sum_wd_pp(t) > wd_limit_pp(t):
        g = min(g * excess_factor(t), gwb_pp_at(t, BenefitTiming.BEF_ANNIV))
    if timing == BenefitTiming.BEF_ANNIV:
        return g
    raise ValueError('invalid timing')


def gawa_pp(t):
    if depleted_flag(t - 1):
        return gawa_pp_init() if t == 0 else gawa_pp(t - 1)
    g = gawa_pp_at(t, BenefitTiming.BEF_ANNIV)
    if is_anniv(t):
        pct = gawa_pct_fixed(t)
        if has_wd_by(t) and pct > 0.0:
            if bonus_pp(t) > 0.0:
                g = max(pct * gwb_pp_aft_bonus(t), g)
            if is_stepup(t):
                g = max(pct * gwb_pp_aft_stepup(t), g)
        if not forlife_flag() and gwb_pp(t) < g:
            g = gwb_pp(t)
    if g <= 0.0 and depleted_flag(t) and (gawa_pct_fixed(t) > 0.0):
        g = gawa_pct_fixed(t) * gwb_pp(t)
    return g


def rp_reduction_pp(t):
    if t < 0 or wd_pp(t) <= 0.0:
        return 0.0
    rp = (rp_pp_init() if t == 0 else rp_pp(t - 1)) + premium_pp(t)
    earnings = max(0.0, av_pp_at(t, AvTiming.BEF_WD) - rp)
    return min(rp, max(0.0, wd_pp(t) - earnings))


def rb_prior_anniv_pp(t):
    u = t_of_month(12 * (policy_year(t) - 1) - 1)
    return rb_pp(u) if u >= 0 else rb_pp_at(0, BenefitTiming.BEF_WD)


def gmdb_wd_dfd_pp(t):
    if t < 0 or wd_pp(t) <= 0.0 or gmdb_option() != GmdbOption.rollup:
        return 0.0
    used = 0.0 if t == 0 or is_year_start(t) else gmdb_dfd_acc_pp(t - 1)
    return min(wd_pp(t), max(0.0, gmdb_allow_pp(t) - used))


def gmdb_wd_excess_pp(t):
    if t < 0 or gmdb_option() != GmdbOption.rollup:
        return 0.0
    return wd_pp(t) - gmdb_wd_dfd_pp(t)


def gmdb_wd_factor(t):
    if gmdb_wd_excess_pp(t) <= 0.0:
        return 1.0
    base = av_pp_at(t, AvTiming.BEF_WD) - gmdb_wd_dfd_pp(t)
    if base <= 0.0:
        return 0.0
    return max(0.0, 1.0 - gmdb_wd_excess_pp(t) / base)


def rb_pp_at(t, timing):
    r = rb_pp_init() if t == 0 else rb_pp(t - 1)
    if depleted_flag(t - 1):
        return r
    if timing == BenefitTiming.BEF_PREM:
        return r
    r = r + prem_to_av_pp(t)
    if timing == BenefitTiming.BEF_WD:
        return r
    if wd_pp(t) > 0.0 and gmdb_option() != GmdbOption.rollup:
        base = av_pp_at(t, AvTiming.BEF_WD)
        r = r * max(0.0, 1.0 - wd_pp(t) / base) if base > 0.0 else 0.0
    if timing == BenefitTiming.BEF_ANNIV:
        return r
    raise ValueError('invalid timing')


def rb_pp(t):
    if depleted_flag(t - 1):
        return rb_pp_init() if t == 0 else rb_pp(t - 1)
    r = rb_pp_at(t, BenefitTiming.BEF_ANNIV)
    if not is_anniv(t):
        return r
    option = gmdb_option()
    if option == GmdbOption.rollup:
        r = max(0.0, (r - gmdb_dfd_acc_pp(t)) * gmdb_factor_acc(t))
        if age_at_anniv(t) <= gmdb_growth_cutoff_age:
            r = r * (1.0 + rollup_rate(t))
    elif option == GmdbOption.HQAV:
        if age_at_anniv(t) <= gmdb_growth_cutoff_age:
            r = max(r, av_pp(t))
    elif option == GmdbOption.basic:
        pass
    else:
        raise ValueError('invalid gmdb_option')
    return r


def gmdb_guarantee_pp(t):
    if gmdb_option() == GmdbOption.basic:
        return rb_pp(t)
    return max(np_pp(t), rb_pp(t))


def mort_rate(t):
    return lookup(mortality_rows(), min(age(t), mortality_max_age), 'mort_rate')


def pols_if(t):
    if t < 0 or t >= proj_len():
        return 0.0
    if t == 0:
        return pols_if_init()
    return pols_if_at(t - 1, PolTiming.AFT_DECR)


def pols_if_at(t, timing):
    if t < 0:
        return 0.0
    pols = pols_if(t)
    if timing == PolTiming.BEF_DECR:
        return pols
    pols = pols * (1.0 - mort_rate_mth(t))
    if timing == PolTiming.BEF_LAPSE:
        return pols
    pols = pols * (1.0 - lapse_rate_mth(t))
    if timing == PolTiming.AFT_DECR:
        return pols
    raise ValueError('invalid timing')


def pols_lapse(t):
    return 0.0 if t < 0 else pols_if_at(t, PolTiming.BEF_LAPSE) * lapse_rate_mth(t)


def pols_maturity(t):
    return pols_if_at(t, PolTiming.AFT_DECR) if t == proj_len() - 1 else 0.0


def pols_decr(t, kind):
    if kind == Kind.DEATH:
        return pols_death(t)
    elif kind == Kind.LAPSE:
        return pols_lapse(t)
    elif kind == Kind.MATURITY:
        return pols_maturity(t)
    else:
        raise ValueError('invalid kind')


def claim_pp(t, kind):
    if kind == Kind.DEATH:
        return db_pp(t)
    elif kind == Kind.LAPSE:
        return surr_benefit_pp(t)
    elif kind == Kind.MATURITY:
        return surr_benefit_pp(t)
    else:
        raise ValueError('invalid kind')


def claim_from_av_pp(t, kind):
    if kind in (Kind.DEATH, Kind.LAPSE, Kind.MATURITY):
        return av_pp(t)
    raise ValueError('invalid kind')


def claims(t, kind=3):
    if kind == Kind.ALL:
        return claims(t, Kind.DEATH) + claims(t, Kind.LAPSE) + claims(t, Kind.MATURITY)
    return claim_pp(t, kind) * pols_decr(t, kind)


def claims_over_av(t, kind=3):
    if kind == Kind.ALL:
        return claims_over_av(t, Kind.DEATH) + claims_over_av(t, Kind.LAPSE) + claims_over_av(t, Kind.MATURITY)
    return claims(t, kind) - claims_from_av(t, kind)


def av_at(t, timing):
    if t < 0:
        return 0.0
    if timing == AvTiming.EOM:
        return av_pp(t) * pols_if(t + 1)
    return av_pp_at(t, timing) * pols_if(t)


def av_change(t):
    opening = av_pp_init() * pols_if_init() if t == 0 else av_at(t - 1, AvTiming.EOM)
    return av_at(t, AvTiming.EOM) - opening


def check_charge_split():
    return all_true(abs(check_charge_split_resid(t)) < 1e-8 for t in range(proj_len()))


def check_pols_roll_fwd():
    return all_true(abs(check_pols_roll_fwd_resid(t)) < 1e-12 for t in range(proj_len()))


def check_av_roll_fwd():
    return all_true(abs(check_av_roll_fwd_resid(t)) < 1e-6 for t in range(proj_len()))


def check_av_roll_fwd_resid(t):
    if t < 0:
        return 0.0
    expected = prem_to_av(t) - wd_from_av(t) + inv_income(t) - charges_from_av(t) - claims_from_av(t, Kind.DEATH) - claims_from_av(t, Kind.LAPSE) - claims_from_av(t, Kind.MATURITY)
    return av_change(t) - expected


def fund_rows():
    return subtable(fund_table, fund_set())


def fund_count():
    return key_count(fund_rows())


def fund_id(index):
    return key_at(fund_rows(), index)


def fund_return_rows(i):
    return subtable(subtable(fund_returns, scenario_id()), i)


def has_transactions():
    return has_group(transaction_table, txn_id())


def transaction_rows():
    return subtable(transaction_table, txn_id())


def charge_rows():
    return subtable(cdsc_table, cdsc_schedule())


def mortality_rows():
    return subtable(mortality_table, sex())


def sub_ids():
    return [fund_id(k) for k in range(fund_count())]


def result_cf():
    ts = list(range(proj_len()))
    return pd.DataFrame(                                             # noqa: F821
        {
            "pols_if": [pols_if(t) for t in ts],
            "premiums": [premiums(t) for t in ts],
            "asset_charges": [asset_charges(t) for t in ts],
            "fees_glwb": [fees_glwb(t) for t in ts],
            "fees_gmdb": [fees_gmdb(t) for t in ts],
            "maint_fees": [maint_fees(t) for t in ts],
            "withdrawals": [withdrawals(t) for t in ts],
            "glwb_payments": [glwb_payments(t) for t in ts],
            "claims_death": [claims(t, Kind.DEATH) for t in ts],
            "claims_lapse": [claims(t, Kind.LAPSE) for t in ts],
            "claims_maturity": [claims(t, Kind.MATURITY) for t in ts],
            "expenses": [expenses(t) for t in ts],
            "commissions": [commissions(t) for t in ts],
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
            "pols_death": [pols_death(t) for t in ts],
            "pols_lapse": [pols_lapse(t) for t in ts],
            "pols_maturity": [pols_maturity(t) for t in ts],
            "pols_if_aft_decr": [pols_if_at(t, PolTiming.AFT_DECR) for t in ts],
        },
        index=pd.Index(ts, name="t"),                                # noqa: F821
    )


def result_av():
    ts = list(range(proj_len()))
    cols = {}
    for i in sub_ids():
        cols["sa_pp_%s" % i] = [sa_pp(t, i) for t in ts]
    cols["av_pp_bef_fee"] = [av_pp_at(t, AvTiming.BEF_FEE) for t in ts]
    cols["fee_glwb_pp"] = [fee_glwb_pp(t) for t in ts]
    cols["fee_gmdb_pp"] = [fee_gmdb_pp(t) for t in ts]
    cols["maint_fee_pp"] = [maint_fee_pp(t) for t in ts]
    cols["asset_charge_pp"] = [asset_charge_pp(t) for t in ts]
    cols["fund_expense_pp"] = [fund_expense_pp(t) for t in ts]
    cols["av_pp"] = [av_pp(t) for t in ts]
    cols["surr_benefit_pp"] = [surr_benefit_pp(t) for t in ts]
    return pd.DataFrame(cols, index=pd.Index(ts, name="t"))


CELLS = (
    'model_point',
    'alloc',
    'fund_expense_rate',
    'inv_return_mth',
    'scenario_rate',
    'sa_pp_at',
    'sa_pp',
    'av_pp_at',
    'av_pp',
    'sa_weight',
    'gross_inv_income_pp',
    'fund_expense_pp',
    'asset_charge_pp',
    'inv_income_pp',
    'prem_scheduled_pp',
    'wd_scheduled_pp',
    'gawa_pct_at_age',
    'wd_limit_pp',
    'wd_pp',
    'cv_pre_excess_pp',
    'free_wd_allow',
    'surr_charge_rate',
    'phi_glwb',
    'phi_gmdb',
    'rollup_rate',
    'fee_glwb_pp_due',
    'fee_gmdb_pp_due',
    'maint_fee_pp_due',
    'charge_scale',
    'gwb_pp_at',
    'bb_pp_bef_anniv',
    'gwb_pp_aft_bonus',
    'stepup_base_pp',
    'gawa_pp_at',
    'gawa_pp',
    'rp_reduction_pp',
    'rb_prior_anniv_pp',
    'gmdb_wd_dfd_pp',
    'gmdb_wd_excess_pp',
    'gmdb_wd_factor',
    'rb_pp_at',
    'rb_pp',
    'gmdb_guarantee_pp',
    'mort_rate',
    'pols_if',
    'pols_if_at',
    'pols_lapse',
    'pols_maturity',
    'pols_decr',
    'claim_pp',
    'claim_from_av_pp',
    'claims',
    'claims_over_av',
    'av_at',
    'av_change',
    'check_av_roll_fwd',
    'check_pols_roll_fwd',
    'check_charge_split',
    'check_av_roll_fwd_resid',
    'fund_rows',
    'fund_count',
    'fund_id',
    'fund_return_rows',
    'has_transactions',
    'transaction_rows',
    'charge_rows',
    'mortality_rows',
    'sub_ids',
    'is_wd_year',
    'result_cf',
    'result_pols',
    'result_av',
)
