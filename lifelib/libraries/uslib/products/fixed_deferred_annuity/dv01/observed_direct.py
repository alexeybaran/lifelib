"""Historical reads for a Valuation assembled with the direct route."""


def observed_av_pp(t):
    return Actual[policy_id, scen_id].av_pp(t)


def observed_mgsv_pp(t):
    return Actual[policy_id, scen_id].mgsv_pp(t)


def observed_interest_credited_pp(t):
    return Actual[policy_id, scen_id].interest_credited_pp(t)


def observed_prem_accum_gmir_pp(t):
    return Actual[policy_id, scen_id].prem_accum_gmir_pp(t)


def observed_pols_if(t):
    return Actual[policy_id, scen_id].pols_if(t)


def observed_free_wd_remain(t):
    return Actual[policy_id, scen_id].free_wd_remain(t)


def observed_tax_basis_pp(t):
    return Actual[policy_id, scen_id].tax_basis_pp(t)


def observed_net_cf(t):
    return Actual[policy_id, scen_id].net_cf(t)


def observed_credit_rate(t):
    return Actual[policy_id, scen_id].credit_rate(t)


def observed_mva_ref_yield_locked(t):
    return Actual[policy_id, scen_id].mva_ref_yield_locked(t)
