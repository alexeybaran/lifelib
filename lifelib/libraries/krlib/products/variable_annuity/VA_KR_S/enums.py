"""Label families passed as cell arguments in VA_KR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class FundTiming(StrEnum):
    BEF_PREM = "BEF_PREM"
    BEF_DEDUCT = "BEF_DEDUCT"
    AFT_DEDUCT = "AFT_DEDUCT"
    AFT_DERISK = "AFT_DERISK"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    ANNUITY = "ANNUITY"
    MATURITY = "MATURITY"


class ChargeLine(StrEnum):
    acq_charge = "acq_charge"
    maint_charge_in = "maint_charge_in"
    maint_charge_after = "maint_charge_after"
    other_charge = "other_charge"
    gmdb_charge = "gmdb_charge"
    gmab_charge_asset = "gmab_charge_asset"
    gmab_charge_prem = "gmab_charge_prem"
    surr_charge = "surr_charge"
    surr_charge_cap = "surr_charge_cap"
    annuity_charge = "annuity_charge"
    fund_expense = "fund_expense"
    comm_yr1 = "comm_yr1"
    comm_yr2 = "comm_yr2"
    comm_yr3 = "comm_yr3"
    comm_yr4 = "comm_yr4"
    comm_yr5 = "comm_yr5"
    expense_acq = "expense_acq"
    expense_maint = "expense_maint"
