"""IntEnum families passed as cell arguments in LTC_JP_S, stored with the model."""

from enum import IntEnum


class Grade(IntEnum):
    support1 = 0
    support2 = 1
    care1 = 2
    care2 = 3
    care3 = 4


class PrevParam(IntEnum):
    prev_ceil = 0
    prev_beta = 1
    prev_x_mid = 2
    prev_age_low = 3
    prev_rate_low = 4
    prev_age_high = 5
    prev_rate_high = 6


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    LUMP = 0
    ANNUITY = 1
    DEMENTIA = 2
    LAPSE = 3
    ALL = 4
