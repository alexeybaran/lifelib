"""Label families passed as cell arguments in Pension_KR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class MortTable(StrEnum):
    annuitant_issue = "annuitant_issue"
    annuitant_revised = "annuitant_revised"


class AnchorItem(StrEnum):
    law_a = "law_a"
    law_b = "law_b"
    law_c = "law_c"
    age_setback = "age_setback"
    omega_age = "omega_age"
    improve_factor = "improve_factor"
    pub_q_40 = "pub_q_40"
    pub_q_50 = "pub_q_50"
    pub_q_60 = "pub_q_60"
    pub_q_70 = "pub_q_70"
    pub_q_80 = "pub_q_80"


class PricingItem(StrEnum):
    prem_freq = "prem_freq"
    annuity_freq = "annuity_freq"
    prem_int_rate = "prem_int_rate"
    avg_decl_rate = "avg_decl_rate"
    acq_charge_rate = "acq_charge_rate"
    acq_charge_years = "acq_charge_years"
    maint_charge_rate = "maint_charge_rate"
    maint_charge_rate_paid_up = "maint_charge_rate_paid_up"
    addl_charge_rate = "addl_charge_rate"
    addl_prem_cap_ratio = "addl_prem_cap_ratio"
    annuity_charge_rate = "annuity_charge_rate"
    min_fund_ratio = "min_fund_ratio"
    mort_be_factor = "mort_be_factor"
    surr_chg_years = "surr_chg_years"
    surr_chg_cap_rate = "surr_chg_cap_rate"
    surr_chg_cap_rate_par = "surr_chg_cap_rate_par"
    surr_chg_cap_term_cap = "surr_chg_cap_term_cap"
    surr_chg_cap_level_years = "surr_chg_cap_level_years"
    loan_rate = "loan_rate"
    loan_draw_frac = "loan_draw_frac"
    loan_draw_year = "loan_draw_year"
    holiday_start_year = "holiday_start_year"
    holiday_max_years = "holiday_max_years"
    div_int_rate = "div_int_rate"


class ExpenseItem(StrEnum):
    expense_acq = "expense_acq"
    expense_maint_defer = "expense_maint_defer"
    expense_maint_payout = "expense_maint_payout"
    expense_claim = "expense_claim"
    inflation_rate = "inflation_rate"
    comm_init_rate = "comm_init_rate"
    comm_renewal_rate = "comm_renewal_rate"


class TaxItem(StrEnum):
    credit_rate_low_income = "credit_rate_low_income"
    credit_rate_high_income = "credit_rate_high_income"
    credit_income_threshold = "credit_income_threshold"
    credit_cap = "credit_cap"
    contribution_ceiling = "contribution_ceiling"
    other_income_tax_rate = "other_income_tax_rate"
    pension_tax_rate_under70 = "pension_tax_rate_under70"
    pension_tax_rate_70to79 = "pension_tax_rate_70to79"
    pension_tax_rate_80plus = "pension_tax_rate_80plus"
    pension_tax_rate_life = "pension_tax_rate_life"
    aggregation_threshold = "aggregation_threshold"
    min_annuity_age = "min_annuity_age"
    min_account_years = "min_account_years"
    limit_denominator_base = "limit_denominator_base"
    limit_uplift = "limit_uplift"


class AvTiming(StrEnum):
    BEF_PREM = "BEF_PREM"
    AFT_PREM = "AFT_PREM"
    AFT_INT = "AFT_INT"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    ANNUITY = "ANNUITY"
    DEATH = "DEATH"
    LAPSE = "LAPSE"
