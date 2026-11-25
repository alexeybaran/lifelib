"""IntEnum families passed as cell arguments in VA_US_S, stored with the model."""

from enum import IntEnum


class RateColumn(IntEnum):
    vix_sq = 0
    cmt10 = 1


class Timing(IntEnum):
    BEF_PREM = 0
    BEF_WD = 1
    BEF_INV = 2
    BEF_FEE = 3
    BEF_ANNIV = 4
    EOM = 5


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Claim(IntEnum):
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
    ALL = 3
