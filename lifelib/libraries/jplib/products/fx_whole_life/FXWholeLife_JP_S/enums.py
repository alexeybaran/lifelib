"""IntEnum families passed as cell arguments in FXWholeLife_JP_S, stored with the model."""

from enum import IntEnum


class ChargeItem(IntEnum):
    prem_charge_early = 0
    prem_charge_late = 1
    prem_charge_early_months = 2
    maint_rate = 3
    coi_charged = 4
    surr_charge_start = 5
    surr_charge_step = 6
    surr_charge_months = 7
    low_cv_ge4 = 8
    low_cv_3 = 9
    low_cv_2 = 10
    low_cv_1 = 11
    mva_spread = 12
    mva_base_rate = 13
    mva_damping = 14
    special_reserve_rate_10 = 15
    special_reserve_rate_20 = 16


class AvTiming(IntEnum):
    BEF_PREM = 0
    AFT_PREM = 1
    AFT_CHARGE_MAINT = 2
    AFT_CHARGE = 3
    AFT_INT = 4


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    ALL = 2
