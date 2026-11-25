"""Label families passed as cell arguments in FXWholeLife_JP_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class ChargeItem(StrEnum):
    prem_charge_early = "prem_charge_early"
    prem_charge_late = "prem_charge_late"
    prem_charge_early_months = "prem_charge_early_months"
    maint_rate = "maint_rate"
    coi_charged = "coi_charged"
    surr_charge_start = "surr_charge_start"
    surr_charge_step = "surr_charge_step"
    surr_charge_months = "surr_charge_months"
    low_cv_ge4 = "low_cv_ge4"
    low_cv_3 = "low_cv_3"
    low_cv_2 = "low_cv_2"
    low_cv_1 = "low_cv_1"
    mva_spread = "mva_spread"
    mva_base_rate = "mva_base_rate"
    mva_damping = "mva_damping"
    special_reserve_rate_10 = "special_reserve_rate_10"
    special_reserve_rate_20 = "special_reserve_rate_20"


class AvTiming(StrEnum):
    BEF_PREM = "BEF_PREM"
    AFT_PREM = "AFT_PREM"
    AFT_CHARGE_MAINT = "AFT_CHARGE_MAINT"
    AFT_CHARGE = "AFT_CHARGE"
    AFT_INT = "AFT_INT"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
