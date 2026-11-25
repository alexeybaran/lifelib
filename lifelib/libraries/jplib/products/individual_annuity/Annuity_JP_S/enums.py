"""Label families passed as cell arguments in Annuity_JP_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class MortTable(StrEnum):
    death_cover_2018 = "death_cover_2018"
    annuity_payout_2007 = "annuity_payout_2007"


class PricingItem(StrEnum):
    int_rate_defer = "int_rate_defer"
    int_rate_payout = "int_rate_payout"
    expense_loading = "expense_loading"
    annuitisation_charge = "annuitisation_charge"
    surr_charge_years = "surr_charge_years"
    surr_charge_prems = "surr_charge_prems"
    mort_be_factor_defer = "mort_be_factor_defer"
    mort_be_factor_payout = "mort_be_factor_payout"
    annuity_round_to = "annuity_round_to"
    div_int_rate = "div_int_rate"
    loan_rate = "loan_rate"
    apl_rate = "apl_rate"
    loan_draw_frac = "loan_draw_frac"
    loan_draw_year = "loan_draw_year"
    lapse_dyn_phi = "lapse_dyn_phi"
    lapse_dyn_cap = "lapse_dyn_cap"
    commute_int_rate = "commute_int_rate"


class ExpenseItem(StrEnum):
    expense_acq = "expense_acq"
    comm_init_rate = "comm_init_rate"
    comm_renewal_rate = "comm_renewal_rate"
    expense_maint_defer = "expense_maint_defer"
    expense_maint_payout = "expense_maint_payout"
    expense_claim = "expense_claim"
    inflation_rate = "inflation_rate"


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
    COMMUTATION = "COMMUTATION"


class Weighting(StrEnum):
    count = "count"
    fund = "fund"
