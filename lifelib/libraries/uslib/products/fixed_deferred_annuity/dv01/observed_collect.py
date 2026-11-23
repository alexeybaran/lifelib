"""Read a policy's observed values from the scenario's detached collect result."""


def observed_policy():
    if valuation_month <= last_snapshot_month:
        return Actual.collect(scen_id).individual[policy_id]
    return Actual.collect(scen_id, valuation_month).individual[policy_id]


def observed_av_pp(t):
    return observed_policy().opening_account_value[t + 1]


def observed_mgsv_pp(t):
    return observed_policy().opening_guaranteed_surrender_value[t + 1]


def observed_interest_credited_pp(t):
    return observed_policy().interest_credited_to_date[t + 1]


def observed_prem_accum_gmir_pp(t):
    return observed_policy().opening_accumulated_guaranteed_premiums[t + 1]


def observed_pols_if(t):
    return observed_policy().pols_if[t]


def observed_free_wd_remain(t):
    return observed_policy().free_wd_remain[t]


def observed_tax_basis_pp(t):
    return observed_policy().tax_basis_pp[t]


def observed_net_cf(t):
    return observed_policy().net_cf[t]


def observed_credit_rate(t):
    return observed_policy().credit_rate[t]


def observed_mva_ref_yield_locked(t):
    return observed_policy().mva_ref_yield_locked[t]
